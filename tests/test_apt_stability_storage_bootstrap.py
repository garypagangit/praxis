"""Run production storage guards with mocked Linux block metadata, without AWS."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


SHELL = Path(__file__).resolve().parents[1] / "experiments/apt_final/normal_stability_continuation/run_cloud.sh"
BASH = Path("C:/Program Files/Git/bin/bash.exe")


def bash_path(path):
    # Preserve aliases so tests exercise the production canonical-path check.
    path = Path(path).absolute().as_posix()
    return "/" + path[0].lower() + path[2:] if len(path) > 1 and path[1] == ":" else path


@unittest.skipUnless(BASH.exists(), "Git Bash required for the Windows bootstrap qualification")
class StorageBootstrap(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "base"
        self.base.mkdir()
        self.sysfs = self.root / "nvme0n1p1"
        self.sysfs.mkdir()
        self.source = SHELL.read_text(encoding="utf-8")
        self.guards = self.source.split("# BEGIN_STABLE_STORAGE_GUARDS\n", 1)[1].split("# END_STABLE_STORAGE_GUARDS", 1)[0]
        self.publish = "publish() {" + self.source.split("publish() {", 1)[1].split("\ntrap publish EXIT", 1)[0]
        self.run_path = self.base / "praxis" / "run1"

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, body, *, mount="/", free_bytes=10737418240, disks=None):
        if disks is None:
            disks = "part\ndisk Amazon Elastic Block Store"
        # Root/device metadata is Linux-specific; file identities, canonical paths,
        # directory replacement, hashing, tar creation and shell flow remain real.
        setup = f"""
set -euo pipefail
TEST_BASE={shlex.quote(bash_path(self.base))}
TEST_SYSFS={shlex.quote(bash_path(self.sysfs))}
MOCK_MOUNT={shlex.quote(mount)}
MOCK_FREE={free_bytes}
MOCK_DISKS={shlex.quote(disks)}
UPLOAD_LOG={shlex.quote(bash_path(self.root / 'uploads.log'))}
findmnt() {{
  if [[ "$3" == MAJ:MIN ]]; then printf '259:1\\n';
  elif [[ "$3" == TARGET ]]; then printf '%s\\n' "$MOCK_MOUNT";
  else return 90; fi
}}
readlink() {{
  if [[ "${{@: -1}}" == /sys/dev/block/259:1 ]]; then printf '%s\\n' "$TEST_SYSFS";
  else command readlink "$@"; fi
}}
stat() {{
  if [[ "${{@: -1}}" == / ]]; then command stat -Lc '%d' -- "$TEST_BASE";
  else command stat "$@"; fi
}}
lsblk() {{ printf '%s\\n' "$MOCK_DISKS"; }}
df() {{ printf 'Filesystem 1-blocks Used Available Use%% Mounted\\n/dev/nvme0n1p1 99999999999 1 %s 1%% /\\n' "$MOCK_FREE"; }}
timeout() {{ shift; "$@"; }}
aws() {{ printf '%s\\n' "$*" >> "$UPLOAD_LOG"; }}
"""
        script = self.root / "case.sh"
        script.write_text(setup + self.guards + "\n" + body + "\n", encoding="utf-8", newline="\n")
        result = subprocess.run([str(BASH), "--noprofile", "--norc", bash_path(script)], capture_output=True,
                                text=True, timeout=20, env={**os.environ, "MSYS2_ARG_CONV_EXCL": "*"})
        return result

    def test_production_shell_syntax(self):
        result = subprocess.run([str(BASH), "-n", bash_path(SHELL)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stable_nvme_ebs_and_exact_ten_gib_boundary_pass(self):
        result = self.execute('prepare_run_storage "$TEST_BASE" praxis run1\nassert_run_storage')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.run_path / "outputs" / "ENV_SELECTION.log").is_file())

    def test_low_disk_is_rejected_before_unique_run_directory_creation(self):
        result = self.execute('prepare_run_storage "$TEST_BASE" praxis run1', free_bytes=10737418239)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least 10 GiB", result.stderr)
        self.assertFalse(self.run_path.exists())

    def test_other_mount_is_rejected_before_run_creation(self):
        result = self.execute('prepare_run_storage "$TEST_BASE" praxis run1', mount="/mnt/ephemeral")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verified root filesystem", result.stderr)
        self.assertFalse(self.run_path.exists())

    def test_non_ebs_or_mixed_backing_disks_are_rejected(self):
        for disks in ("part\ndisk Amazon EC2 NVMe Instance Storage",
                      "part\ndisk Amazon Elastic Block Store\ndisk Amazon EC2 NVMe Instance Storage",
                      "part\ncrypt"):
            result = self.execute('prepare_run_storage "$TEST_BASE" praxis run1', disks=disks)
            with self.subTest(disks=disks):
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("not all verified Amazon EBS", result.stderr)
                self.assertFalse(self.run_path.exists())

    def test_existing_run_and_unsafe_identifiers_are_rejected(self):
        self.run_path.mkdir(parents=True)
        result = self.execute('prepare_run_storage "$TEST_BASE" praxis run1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing run directory", result.stderr)
        for parent, name in (("../unsafe", "run2"), ("praxis", "../run2")):
            result = self.execute(f'prepare_run_storage "$TEST_BASE" {shlex.quote(parent)} {shlex.quote(name)}')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid storage directory identifier", result.stderr)

    def test_symlink_base_is_rejected_when_platform_supports_symlinks(self):
        alias = self.root / "alias"
        try:
            alias.symlink_to(self.base, target_is_directory=True)
        except OSError as error:
            # An NTFS directory junction exercises the same alias rejection
            # without the Windows privilege required for native symlinks.
            junction = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(self.base)],
                                      capture_output=True, text=True, timeout=10)
            if junction.returncode != 0:
                self.skipTest("Windows symlink/junction creation unavailable: " + str(error))
        result = self.execute(f'prepare_run_storage {shlex.quote(bash_path(alias))} praxis run1')
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, "non-symlink directory|no symlink components")

    def test_replaced_outputs_inode_is_rejected(self):
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
mv "$run_dir/outputs" "$run_dir/outputs_original"
mkdir "$run_dir/outputs"
assert_run_storage''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("device/inode changed", result.stderr)

    def test_mount_change_is_rejected_after_initial_pin(self):
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
MOCK_MOUNT=/mnt/replaced
assert_run_storage''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verified root filesystem", result.stderr)

    def test_mock_download_path_change_is_caught_before_worker_marker(self):
        # Execute the exact production download/checksum segment. aws returns
        # success while replacing the output directory, matching the failure class.
        segment = "timeout 180 aws s3 cp " + self.source.split("timeout 180 aws s3 cp ", 1)[1].split("python3 - <<'PY'", 1)[0]
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
bundle_uri=s3://synthetic/bundle
bundle_sha=0000000000000000000000000000000000000000000000000000000000000000
aws() { mv "$run_dir/outputs" "$run_dir/outputs_original"; mkdir "$run_dir/outputs"; return 0; }
''' + segment + '\ntouch "$run_dir/WORKER_STARTED"')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("device/inode changed", result.stderr)
        self.assertFalse((self.run_path / "WORKER_STARTED").exists())

    def test_publication_preserves_original_failure_and_uploads_archive_with_checksum(self):
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
output_uri=s3://synthetic/result
''' + self.publish + '''
set +e
(exit 7)
publish''')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual((self.run_path / "outputs" / "WORKER_EXIT.txt").read_text().strip(), "7")
        self.assertTrue((self.run_path / "result.tar.gz").is_file())
        self.assertEqual(len((self.root / "uploads.log").read_text().splitlines()), 2)

    def test_publication_refuses_replaced_storage_without_recreating_or_uploading(self):
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
output_uri=s3://synthetic/result
''' + self.publish + '''
mv "$run_dir/outputs" "$run_dir/outputs_original"
true
publish''')
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertIn("Evidence path was not recreated", result.stderr)
        self.assertFalse((self.run_path / "outputs").exists())
        self.assertFalse((self.root / "uploads.log").exists())

    def test_publication_upload_failure_is_reported_as_failure(self):
        result = self.execute('''prepare_run_storage "$TEST_BASE" praxis run1
output_uri=s3://synthetic/result
aws() { return 1; }
''' + self.publish + '''
true
publish''')
        self.assertEqual(result.returncode, 91, result.stderr)
        self.assertIn("archive, checksum, or upload failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
