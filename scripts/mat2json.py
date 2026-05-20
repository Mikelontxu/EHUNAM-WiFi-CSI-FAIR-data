import scipy.io
import hashlib
import json
import re

def parse_filename(filename):
    # MC1_01A_2_PC_eabc_W_#_#.mat
    parts = filename.replace(".mat", "").split("_")
    return {
        "campaign": parts[0],
        "set": f"{parts[0]}_{parts[1]}",
        "receiver": parts[2],
        "application": parts[3],
        "people": list(parts[4]),
        "activity": parts[5],
        "machine": parts[6],
        "status": parts[7]
    }

def extract_metadata(filepath):
    mat = scipy.io.loadmat(filepath)
    skip = {"CSI", "RSSI", "TimeStamp", "__header__", "__version__", "__globals__"}
    
    metadata = {k: v.tolist() if hasattr(v, 'tolist') else v 
                for k, v in mat.items() if k not in skip}
    
    checksum = hashlib.sha256(open(filepath, "rb").read()).hexdigest()
    filename_meta = parse_filename(filepath.split("/")[-1])
    
    return {**metadata, **filename_meta, "sha256": checksum}