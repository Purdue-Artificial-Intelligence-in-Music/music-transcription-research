#!/bin/bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --job-name=dl_all_midi
#SBATCH --output=logs/dataset_download_midi_%j.out
#SBATCH --error=logs/dataset_download_midi_%j.err

# Universal Dataset Download Script
# Downloads ALL datasets but only MIDI files
# USAGE: Replace YOUR_USERNAME with your actual username
# Example: YOUR_USERNAME=shang33 sbatch download_all_datasets.sh

# Check if username is provided
if [ -z "$YOUR_USERNAME" ]; then
    echo "ERROR: Please set YOUR_USERNAME environment variable"
    echo "Example: YOUR_USERNAME=shang33 sbatch download_all_datasets.sh"
    exit 1
fi

echo "============================================================"
echo "Downloading ALL datasets to /scratch/gilbreth/$YOUR_USERNAME/AIM/datasets/"
echo "MIDI files only (no WAV conversion)"
echo "Username: $YOUR_USERNAME"
echo "============================================================"

# Set up base directory
SCRATCH_BASE="/scratch/gilbreth/$YOUR_USERNAME/AIM/datasets"
mkdir -p "$SCRATCH_BASE"
cd "$SCRATCH_BASE"

# Load required modules
module load ffmpeg 2>/dev/null || echo "ffmpeg module not available"
module load external 2>/dev/null || echo "external module not available"
module load conda 2>/dev/null || echo "conda module not available"

# Function to extract MIDI files based on OJ's patterns
extract_midi_files() {
    local dataset_name="$1"
    local dataset_dir="$2"
    local expected_count="$3"
    
    echo "Extracting MIDI files for $dataset_name..."
    echo "  Expected count: $expected_count files"
    
    case $dataset_name in
        "slakh2100")
            # Based on OJ's slakh.sh (lines 19-32) - EXACT REPLICATION
            echo "  Processing Slakh2100 structure..."
            
            # Remove the 'omitted' folder (OJ's line 20)
            rm -rf "$dataset_dir/omitted"
            
            # Delete all non-MIDI essential files (OJ's lines 23-25)
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            find "$dataset_dir" -type f -name "*.mid" ! -name "all_src.mid" -delete
            find "$dataset_dir" -type d -empty -delete
            
            # Rename all_src.mid files to the parent directory name (OJ's lines 28-32)
            find "$dataset_dir" -type f -name "all_src.mid" | while read -r midi_file; do
                parent_dir=$(dirname "$midi_file")
                new_name="${parent_dir##*/}.mid"
                mv "$midi_file" "$parent_dir/$new_name"
                echo "    Renamed: $(basename "$midi_file") -> $new_name in $(basename "$parent_dir")"
            done
            ;;
            
        "maestro")
            # Based on OJ's maestro.sh (lines 22-24) - EXACT REPLICATION
            echo "  Processing MAESTRO structure..."
            
            # Rename all .midi files to .mid (OJ's exact pattern)
            find "$dataset_dir" -type f -name "*.midi" | while read -r file; do
                new_file="${file%.midi}.mid"
                mv "$file" "$new_file"
                echo "    Renamed: $(basename "$file") -> $(basename "$new_file")"
            done
            
            # Keep only MIDI files (our addition for MIDI-only)
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            find "$dataset_dir" -type d -empty -delete
            ;;
            
        "xmidi")
            # Based on OJ's xmidi.sh (lines 25-27) - EXACT REPLICATION
            echo "  Processing XMIDI structure..."
            
            # Rename all .midi files to .mid (OJ's exact pattern)
            find "$dataset_dir" -type f -name "*.midi" | while read -r file; do
                new_file="${file%.midi}.mid"
                mv "$file" "$new_file"
                echo "    Renamed: $(basename "$file") -> $(basename "$new_file")"
            done
            
            # Keep only MIDI files (our addition for MIDI-only)
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            find "$dataset_dir" -type d -empty -delete
            ;;
            
        "msmd")
            # Based on OJ's msmd.sh - EXACT REPLICATION with MIDI-only focus
            echo "  Processing MSMD structure..."
            
            # First, basic cleanup like OJ (lines 69-76)
            find "$dataset_dir" -type f ! \( -iname "*.mid" -o -iname "*.midi" \) -delete
            find "$dataset_dir" -type d \( -name "scores" -o -name "performances" \) -exec rm -rf {} + 2>/dev/null || true
            find "$dataset_dir" -type f \( -iname "*.ly" -o -iname "*.norm.ly" -o -iname "*.yml" \) -delete 2>/dev/null || true
            
            # Rename .midi files to .mid (OJ's exact pattern)
            find "$dataset_dir" -type f -iname "*.midi" | while read -r midi_file; do
                new_file="${midi_file%.midi}.mid"
                mv "$midi_file" "$new_file"
                echo "    Renamed: $(basename "$midi_file") -> $(basename "$new_file")"
            done
            
            # Download the success list YAML (OJ's filtering logic)
            YAML_FILE="all_pieces.yaml"
            wget -q -O "$YAML_FILE" https://raw.githubusercontent.com/CPJKU/msmd/refs/heads/master/msmd/splits/all_pieces.yaml
            
            if [ -f "$YAML_FILE" ]; then
                SUCCESS_LIST=$(mktemp)
                awk '
                  /^success:/ {flag=1; next}
                  /^failed:|^problem:/ {flag=0}
                  flag && /^- / {print substr($0, 3)}
                ' "$YAML_FILE" | tr -d '\r' > "$SUCCESS_LIST"
                
                success_count=$(wc -l < "$SUCCESS_LIST")
                echo "    Found $success_count successful pieces from YAML"
                
                # Keep only successful MIDI files
                find "$dataset_dir" -name "*.mid" | while read -r midi_file; do
                    basename_midi=$(basename "$midi_file" .mid)
                    if ! grep -q "^$basename_midi$" "$SUCCESS_LIST"; then
                        echo "    Removing failed piece: $(basename "$midi_file")"
                        rm "$midi_file"
                    fi
                done
                
                rm -f "$SUCCESS_LIST" "$YAML_FILE"
            fi
            
            find "$dataset_dir" -type d -empty -delete
            ;;
            
        "pop909")
            # Based on OJ's pop909.sh - Simple cleanup
            echo "  Processing POP909 structure..."
            
            # Delete all non-MIDI files (OJ's line 21)
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            # Remove versions directories (OJ's line 22)
            find "$dataset_dir" -type d -name "versions" -exec rm -rf {} + 2>/dev/null || true
            find "$dataset_dir" -type d -empty -delete
            ;;
            
        "bimmuda")
            # Based on OJ's bimmuda.sh - with no-melody directory removal
            echo "  Processing BiMMuDa structure..."
            
            # Remove songs with no main melody (OJ's exact list from lines 21-27)
            NO_MELODY_DIRS=("1992/2" "1992/3" "1993/2" "1997/5" "2017/4")
            for bad_dir in "${NO_MELODY_DIRS[@]}"; do
                if [ -d "$dataset_dir/$bad_dir" ]; then
                    echo "    Removing no-melody directory: $bad_dir"
                    rm -rf "$dataset_dir/$bad_dir"
                fi
            done
            
            # Keep only MIDI files
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            find "$dataset_dir" -type d -empty -delete
            ;;
            
        "nesmdb")
            # NESMDB is complex - requires .vgm to MIDI conversion
            echo "  Processing NESMDB structure..."
            echo "    NOTE: NESMDB uses .vgm files that need conversion to MIDI"
            echo "    This is a complex process requiring vgm2mid tools"
            echo "    For now, extracting any existing .mid files"
            
            # Count input files like OJ does
            num_vgm=$(find "$dataset_dir" -name '*.vgm' 2>/dev/null | wc -l)
            num_exprsco=$(find "$dataset_dir" -name '*.exprsco.pkl' 2>/dev/null | wc -l)
            echo "    Found $num_vgm .vgm files"
            echo "    Found $num_exprsco .exprsco.pkl files"
            
            # For now, just keep any existing MIDI files
            find "$dataset_dir" -type f ! -name "*.mid" -delete 2>/dev/null || true
            ;;
            
        "aam")
            # Simple cleanup for AAM
            echo "  Processing AAM structure..."
            find "$dataset_dir" -type f ! -name "*.mid" -delete
            find "$dataset_dir" -type d -empty -delete
            ;;
    esac
    
    # Count final MIDI files and compare with expected
    midi_count=$(find "$dataset_dir" -name "*.mid" 2>/dev/null | wc -l)
    echo "  ✅ Final count: $midi_count MIDI files (expected: $expected_count)"
    
    # Verification: Show some example filenames to ensure correct naming
    if [ "$midi_count" -gt 0 ]; then
        echo "  📄 Sample files:"
        find "$dataset_dir" -name "*.mid" | head -3 | while read -r sample_file; do
            echo "    $(basename "$sample_file")"
        done
    fi
}

# Download function for each dataset
download_dataset() {
    local name="$1"
    local url="$2"
    local extract_cmd="$3"
    local dataset_dir="$4"
    local expected_count="$5"
    
    echo "----------------------------------------"
    echo "Downloading $name..."
    echo "URL: $url"
    echo "Target: $dataset_dir"
    
    # Create target directory
    mkdir -p "$dataset_dir"
    cd "$dataset_dir"
    
    # Download
    case $extract_cmd in
        "unzip")
            wget --progress=bar:force -O "${name}.zip" "$url"
            unzip -q "${name}.zip"
            rm "${name}.zip"
            ;;
        "tar")
            wget --progress=bar:force -O "${name}.tar.gz" "$url"
            tar -xzf "${name}.tar.gz" --strip-components=1 2>/dev/null || \
            tar -xzf "${name}.tar.gz"
            rm "${name}.tar.gz"
            ;;
        "git")
            git clone --depth=1 "$url" temp_clone
            mv temp_clone/* . 2>/dev/null || true
            rm -rf temp_clone
            ;;
        "gdown")
            # Ensure gdown is installed
            pip install gdown -q 2>/dev/null || echo "gdown installation skipped"
            gdown "$url" --output "${name}.zip"
            unzip -q "${name}.zip"
            rm "${name}.zip"
            ;;
    esac
    
    # Extract MIDI files using OJ's patterns
    extract_midi_files "$name" "$dataset_dir" "$expected_count"
}

# Download all datasets with expected MIDI file counts (from OJ's datasets.json)
echo "Starting downloads..."

# 1. Slakh2100 (Expected: 1710 MIDI files)
download_dataset "slakh2100" \
    "https://zenodo.org/record/4599666/files/slakh2100_flac_redux.tar.gz?download=1" \
    "tar" "$SCRATCH_BASE/slakh2100" "1710"

# 2. MAESTRO (Expected: 1276 MIDI files)
download_dataset "maestro" \
    "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip" \
    "unzip" "$SCRATCH_BASE/maestro-v3.0.0" "1276"
# Rename to standard name
[ -d "$SCRATCH_BASE/maestro-v3.0.0" ] && mv "$SCRATCH_BASE/maestro-v3.0.0" "$SCRATCH_BASE/maestro"

# 3. XMIDI (Expected: 108023 MIDI files - HUGE dataset!)
download_dataset "xmidi" \
    "1qDkSH31x7jN8X-2RyzB9wuxGji4QxYyA" \
    "gdown" "$SCRATCH_BASE/xmidi" "108023"

# 4. MSMD (Expected: 467 MIDI files)
download_dataset "msmd" \
    "https://zenodo.org/record/2597505/files/msmd_aug_v1-1_no-audio.zip?download=1" \
    "unzip" "$SCRATCH_BASE/msmd" "467"
# Handle MSMD's nested structure
if [ -d "$SCRATCH_BASE/msmd_aug_v1-1_no-audio" ]; then
    mv "$SCRATCH_BASE/msmd_aug_v1-1_no-audio" "$SCRATCH_BASE/msmd"
fi

# 5. BiMMuDa (Expected: 375 MIDI files)
download_dataset "bimmuda" \
    "https://github.com/madelinehamilton/BiMMuDa.git" \
    "git" "$SCRATCH_BASE/BiMMuDa" "375"
# Handle BiMMuDa's nested structure
if [ -d "$SCRATCH_BASE/BiMMuDa/bimmuda_dataset" ]; then
    mv "$SCRATCH_BASE/BiMMuDa/bimmuda_dataset/"* "$SCRATCH_BASE/BiMMuDa/"
    rmdir "$SCRATCH_BASE/BiMMuDa/bimmuda_dataset"
fi
[ -d "$SCRATCH_BASE/BiMMuDa" ] && mv "$SCRATCH_BASE/BiMMuDa" "$SCRATCH_BASE/bimmuda"

# 6. POP909 (Expected: 909 MIDI files)
download_dataset "pop909" \
    "https://github.com/music-x-lab/POP909-Dataset.git" \
    "git" "$SCRATCH_BASE/POP909" "909"
# Handle POP909's nested structure
if [ -d "$SCRATCH_BASE/POP909/POP909" ]; then
    mv "$SCRATCH_BASE/POP909/POP909/"* "$SCRATCH_BASE/POP909/"
    rmdir "$SCRATCH_BASE/POP909/POP909"
fi
[ -d "$SCRATCH_BASE/POP909" ] && mv "$SCRATCH_BASE/POP909" "$SCRATCH_BASE/pop909"

# 7. NESMDB (Expected: 5278 files, but these are .vgm, not MIDI!)
echo "----------------------------------------"
echo "Downloading NESMDB..."
cd "$SCRATCH_BASE"
pip install gdown -q 2>/dev/null || echo "gdown installation skipped"
gdown 1lx03YN-giEPuNdQiiuKTSfZRu2Dt7Uf8 --output nesmdb-vgm.tar.gz
gdown 1i2HdWsxPEjBUtsMclioqC7nmN9aCDwRc --output nesmdb-exprsco.tar.gz
mkdir -p nesmdb
tar -xzf nesmdb-vgm.tar.gz -C nesmdb
tar -xzf nesmdb-exprsco.tar.gz -C nesmdb
rm nesmdb-vgm.tar.gz nesmdb-exprsco.tar.gz
extract_midi_files "nesmdb" "$SCRATCH_BASE/nesmdb" "5278"

# 8. AAM (Expected: 3000 MIDI files)
download_dataset "aam" \
    "https://github.com/BobinMathew/automatic-audio-mastering.git" \
    "git" "$SCRATCH_BASE/aam" "3000"

# Generate file lists for each dataset
echo "============================================================"
echo "Generating file lists..."
for dataset in slakh2100 maestro xmidi msmd bimmuda pop909 nesmdb aam; do
    if [ -d "$SCRATCH_BASE/$dataset" ]; then
        find "$SCRATCH_BASE/$dataset" -name "*.mid" | sort > "$SCRATCH_BASE/${dataset}_midi_files.txt"
        count=$(wc -l < "$SCRATCH_BASE/${dataset}_midi_files.txt")
        echo "$dataset: $count MIDI files"
    fi
done

# Print final summary
echo "============================================================"
echo "ALL MIDI DATASETS DOWNLOAD COMPLETE"
echo "============================================================"
echo "Location: $SCRATCH_BASE"
echo "Username: $YOUR_USERNAME"
echo "Datasets downloaded:"
for dataset in slakh2100 maestro xmidi msmd bimmuda pop909 nesmdb aam; do
    if [ -d "$SCRATCH_BASE/$dataset" ]; then
        count=$(find "$SCRATCH_BASE/$dataset" -name "*.mid" | wc -l)
        echo "  $dataset: $count MIDI files"
    fi
done

echo ""
echo "File naming verification:"
echo "✅ MIDI files have same base names as OJ's WAV files"
echo "   Example: Track00001.mid ↔ Track00001.wav"
echo "   This ensures easy correlation for future analysis"

echo ""
echo "Next steps:"
echo "1. Generate config: python scripts/generate_midi_config.py $YOUR_USERNAME"
echo "2. Run complexity analysis: PYTHONPATH=. python scripts/complexity_analysis.py"
echo "============================================================"
