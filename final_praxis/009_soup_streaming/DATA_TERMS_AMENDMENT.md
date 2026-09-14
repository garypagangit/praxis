# 009 data-terms clarification before GPU outcomes

September 14, 2026. This source-only amendment preserves the numerical hypotheses and controls in the frozen [qualification protocol](QUALIFICATION_PROTOCOL.md). The original protocol SHA256 is `042559776af19736332c95664729a72876927544495f719639afbcd73264394b`.

The pinned `dair-ai/emotion` card has `license: other` metadata, but its [Licensing Information](https://huggingface.co/datasets/dair-ai/emotion/blob/cab853a1dbdf4c42c2b3ef2173804746df8825fe/README.md#licensing-information) explicitly permits educational and research use. This supports the proposed research use. Unrestricted redistribution remains unverified; raw data stay outside Git. The initial metadata-only concern must not be presented as a prohibition on research.

The three pinned Parquet files were downloaded to the external cache and their schemas and row counts inspected: training 16,000, validation 2,000, test 2,000. All have text and integer-label fields. Hashes and source URLs are retained in `results/SOURCE_DATA_GATE.json`; no raw text is included there.

The August 13 v3 paper was retrieved and inspected: DOI `10.5281/zenodo.21918325`, PDF SHA256 `132580e07ceb34f774eb8dd929b36d99f2c0aba76ff4ecb8f6c05de1489d1992`, 37 pages. The five 3,000-example training subsets and fixed 300-example test panel agree with the earlier description. The exact original preparation script remains unarchived in the inspected Soup tree. A new split would be a declared adapted reproduction, not exact recovery of the published quality experiment.

No GPU result, pretrained quality outcome, hypothesis threshold, or execution assignment motivated this clarification. The random-model instrumentation gate remains independent of this dataset.
