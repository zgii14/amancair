import hashlib
import json

def compute_hash(prev_hash, payload_dict):
    payload = json.dumps(payload_dict, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256((prev_hash + payload).encode('utf-8')).hexdigest()

def append_audit(entry, audit_path="D:/Agent 2/spj-agent/log/audit.jsonl"):
    # Read last hash
    prev_hash = "0" * 64
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                last = json.loads(lines[-1])
                prev_hash = last.get("hash", prev_hash)
    except FileNotFoundError:
        pass
    
    payload = {k: v for k, v in entry.items() if k not in ("hash", "prev_hash")}
    h = compute_hash(prev_hash, payload)
    entry["prev_hash"] = prev_hash
    entry["hash"] = h
    
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return h

if __name__ == "__main__":
    import sys
    # usage: python audit_helper.py '{"waktu":"...","kasus":"...",...}'
    entry = json.loads(sys.argv[1])
    h = append_audit(entry)
    print(h)
