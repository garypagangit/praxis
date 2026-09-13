"""Reconstruct the frozen public cohort and prompt manifest without model inference."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata
import urllib.request

HERE = Path(__file__).resolve().parent


def sha(value):
    return hashlib.sha256(value).hexdigest()


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources-dir', type=Path, required=True)
    parser.add_argument('--tokenizer-dir', type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads((HERE / 'data_receipt.json').read_text(encoding='utf-8'))
    protocol = json.loads((HERE / 'protocol.json').read_text(encoding='utf-8'))
    args.sources_dir.mkdir(parents=True, exist_ok=True)
    sources = {}
    for split, item in receipt['source_files'].items():
        path = args.sources_dir / (split + '.jsonl')
        if not path.exists():
            raw = urllib.request.urlopen(item['url'], timeout=45).read()
            if sha(raw) != item['sha256']:
                raise ValueError('Downloaded source hash mismatch')
            path.write_bytes(raw)
        raw = path.read_bytes()
        if sha(raw) != item['sha256']:
            raise ValueError('Local source hash mismatch')
        sources[split] = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
        if len(sources[split]) != item['rows']:
            raise ValueError('Source row count mismatch')
    excluded = {normalized(row['question']) for row in sources['test']}
    excluded.update(normalized(sources['train'][int(identity.split('-')[1])]['question'])
                    for identity in receipt['excluded_prior_train_ids'])
    eligible, seen = [], set()
    for index, row in enumerate(sources['train']):
        key = normalized(row['question'])
        if key in excluded or key in seen:
            continue
        seen.add(key)
        eligible.append({'id': f'train-{index:04d}', 'source_index': index, **row,
                         'gold': row['answer'].split('####')[-1].strip(),
                         'question_sha256': sha(row['question'].encode())})
    eligible.sort(key=lambda row: (sha(('completion-format-v1:train:' + row['question']).encode()), row['source_index']))
    if len(eligible) != receipt['eligible_train_n']:
        raise ValueError('Eligible cohort count mismatch')
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer_dir.resolve()), local_files_only=True)
    if sha(tokenizer.chat_template.encode()) != receipt['chat_template_sha256']:
        raise ValueError('Chat template mismatch')
    if sha((args.tokenizer_dir / 'tokenizer.json').read_bytes()) != receipt['tokenizer_json_sha256']:
        raise ValueError('Tokenizer hash mismatch')
    data = {'pilot': eligible[:32]}
    for row in data['pilot']:
        raw = f"Q: {row['question']}\nA: Let's think step by step."
        messages = [{'role': 'user', 'content': raw}]
        kwargs = {'add_generation_prompt': True, 'date_string': protocol['chat_date_string']}
        chat = tokenizer.apply_chat_template(messages, tokenize=False, **kwargs)
        raw_ids = tokenizer(raw, add_special_tokens=True)['input_ids']
        chat_ids = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False, **kwargs)
        if tokenizer(chat, add_special_tokens=False)['input_ids'] != chat_ids:
            raise ValueError('Chat tokenization disagrees')
        row['prompts'] = {}
        for arm, text, ids in [('raw', raw, raw_ids), ('chat', chat, chat_ids)]:
            if ids[0] != 128000 or ids.count(128000) != 1:
                raise ValueError('Exactly one BOS required')
            row['prompts'][arm] = {'text': text, 'prompt_sha256': sha(text.encode()),
                                   'input_token_ids': ids,
                                   'input_token_ids_sha256': sha(json.dumps(ids, separators=(',', ':')).encode()),
                                   'prompt_tokens': len(ids)}
    reconstructed = (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if sha(reconstructed) != protocol['data_sha256'] or reconstructed != (HERE / 'data.json').read_bytes():
        raise ValueError('Reconstructed cohort/prompt bytes differ from preregistration')
    print(json.dumps({'status': 'EXACT_DATA_REPRODUCTION_PASSED', 'pilot_n': 32,
                      'data_sha256': sha(reconstructed), 'model_calls': 0}))


if __name__ == '__main__':
    main()
