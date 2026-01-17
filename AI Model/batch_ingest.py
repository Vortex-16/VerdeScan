import os
import shutil
import uuid
import json
import sys
from pathlib import Path
from datetime import datetime

# Setup paths (Assuming script is in AI Model root)
BASE_DIR = Path(__file__).parent.parent
DATA_DIRS = [
    BASE_DIR / "Data/Image/Drone image",
    BASE_DIR / "Data/Image/Raw Data"
]
UPLOADS_SOURCE_DIR = Path("data/uploads") # Relative to CWD (AI Model)
RESULTS_FILE = Path("data/results.json")

# Ensure we can import core modules
sys.path.append(str(Path(__file__).parent))

from dataclasses import asdict
from core.forest_processor import ForestMLProcessor
from models.data_structures import TreeStatus
import gc

def json_converter(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, TreeStatus):
        return obj.value
    if hasattr(obj, 'value'): # Generic Enum
        return obj.value
    raise TypeError(f"Type {type(obj)} not serializable")

def process_all():
    print(f"Initializing Processor...")
    processor = ForestMLProcessor()
    
    # Ensure uploads dir exists
    UPLOADS_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load existing results
    results = {}
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r') as f:
            try:
                results = json.load(f)
            except:
                pass

    total_files = 0
    processed_files = 0
    
    # Track existing filenames to avoid duplicates if re-running
    existing_files = {r['metadata'].get('original_path') for r in results.values() if 'metadata' in r}

    for data_dir in DATA_DIRS:
        if not data_dir.exists():
            print(f"Skipping missing dir: {data_dir}")
            continue
            
        print(f"Scanning {data_dir}...")
        
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    src_path = Path(root) / file
                    
                    total_files += 1
                    
                    folder_name = Path(root).name
                    # Create a readable patch ID
                    patch_id = f"{folder_name} {file}"
                    
                    print(f"[{processed_files+1}] Processing: {patch_id}")

                    # Generate unique filename for serving
                    file_uuid = str(uuid.uuid4())
                    ext = src_path.suffix
                    stored_filename = f"{file_uuid}_{file}" # Keep original name part for debug
                    stored_path = UPLOADS_SOURCE_DIR / stored_filename
                    
                    # Copy file
                    try:
                        shutil.copy2(src_path, stored_path)
                    except Exception as e:
                        print(f"Failed to copy {src_path}: {e}")
                        continue
                    
                    # Process
                    try:
                        result = processor.process_image(str(stored_path), patch_id)
                        
                        if result:
                            # Manual serialization because dataclasses don't allow methods and properties easily in asdict
                            res_dict = asdict(result)
                            
                            # Add computed property
                            res_dict['summary'] = result.summary_stats
                            
                            # Rename tree_results to details to match frontend expectation
                            res_dict['details'] = res_dict.pop('tree_results', [])
                            
                            # Rename image_metadata to metadata to match frontend expectation (results.json format)
                            res_dict['metadata'] = res_dict.pop('image_metadata')
                            
                            # Inject correct filename for frontend serving
                            res_dict['metadata']['filename'] = stored_filename
                            res_dict['metadata']['original_path'] = str(src_path)
                            
                            results[patch_id] = res_dict
                            processed_files += 1
                            
                            # Save incrementally
                            with open(RESULTS_FILE, 'w') as f:
                                json.dump(results, f, indent=2, default=json_converter)
                        
                        gc.collect() 
                                
                    except Exception as e:
                        print(f"Error processing {patch_id}: {e}")
                        import traceback
                        traceback.print_exc()

    print(f"Done! Processed {processed_files} images.")

if __name__ == "__main__":
    process_all()
