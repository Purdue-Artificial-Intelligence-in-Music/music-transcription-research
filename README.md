# Music Transcription Research

The research progress for the Music Transcription team within AI for Musicians at Purdue University. This project provides a comprehensive framework for evaluating Automatic Music Transcription (AMT) models through automated benchmarking on the Gilbreth computing cluster.

## 🎵 Overview

This repository contains tools and scripts for:
- **Model Evaluation**: Automated testing of multiple AMT models against standardized datasets
- **Performance Scoring**: Comprehensive evaluation using mir_eval metrics with instrument family classification
- **Cluster Computing**: SLURM-based job submission for parallel model evaluation
- **Result Management**: Automated upload and organization of results to Google Drive

## 📁 Project Structure

### Core Scripts
- **`run.py`** - SLURM job submission orchestrator for model evaluation pipeline
- **`scoring.py`** - MIDI transcription evaluation using mir_eval with instrument family analysis
- **`upload.py`** - Google Drive integration for result storage and team notifications
- **`cloning.py`** - Multi-threaded repository cloning for model setup
- **`gilbreth.py`** - Gilbreth cluster deployment and job execution

### Shell Scripts
- **`main.sh`** - Master execution script with environment setup and job control
- **`run.sh`** - Individual model execution with conda environment management
- **`cleanup.sh`** - Post-processing cleanup and resource management

### Configuration Files
- **`models.json`** - Model registry with GitHub repositories and authentication tokens
- **`instrument_families.yaml`** - MIDI instrument classification mapping (128 instruments across 11 families)
- **`service_account.json`** - Google Drive API service account credentials

### Evaluation Datasets
- **`evaluation_mp3/`** - Audio input files for transcription (70+ test files)
- **`evaluation_mid/`** - Ground truth MIDI files for comparison
- **`evaluation_mxl/`** - MusicXML reference scores

### Supporting Files
- **`.gitignore`** - Git ignore patterns for Python, data files, and credentials
- **`LICENSE`** - MIT License for open-source distribution

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- SLURM workload manager (for cluster execution)
- Singularity (for containerized MuseScore conversion)
- Git LFS (for large file handling)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/music-transcription-research.git
   cd music-transcription-research
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure authentication:**
   - Add your Google Drive service account JSON to `service_account.json`
   - Update GitHub tokens in `models.json`

### Local Execution

**Evaluate a single model:**
```bash
python scoring.py --reference evaluation_mid/sample.mid --transcription output/sample.mid
```

**Clone all model repositories:**
```bash
python cloning.py
```

**Upload results to Google Drive:**
```bash
python upload.py --main-folder FOLDER_ID --team-name "ModelName" --local-directory ./results
```

### Cluster Execution

**Deploy to Gilbreth cluster:**
```bash
python gilbreth.py
```

**Submit evaluation jobs:**
```bash
sbatch main.sh
```

## 🔬 Evaluation Methodology

### Scoring Metrics
The project uses `mir_eval.transcription.evaluate()` with the following metrics:
- **Precision, Recall, F-measure** for note onset detection
- **Instrument family classification** accuracy
- **Multi-f0 estimation** performance
- **Average runtime** per audio file

### Instrument Classification
Instruments are grouped into 11 families based on `instrument_families.yaml`:
- **Keyboard** (Piano, Electric Piano, Harpsichord)
- **String** (Violin, Viola, Cello, Harp)
- **Brass** (Trumpet, Trombone, French Horn)
- **Reed** (Saxophone, Clarinet, Oboe)
- **Flute** (Flute, Piccolo, Recorder)
- **Guitar** (Acoustic, Electric, Bass)
- **Bass** (Acoustic Bass, Electric Bass)
- **Organ** (Church Organ, Hammond)
- **Mallet** (Xylophone, Marimba, Vibraphone)
- **Vocal** (Choir, Voice synthesis)
- **Synth Lead** (Various synthesizer leads)

### Test Dataset
The evaluation uses 70+ carefully curated audio samples covering:
- Various instrument combinations
- Different musical genres and complexities
- Mono and polyphonic content
- Clean studio recordings and realistic performance conditions

## 🏗️ Model Integration

### Adding New Models

1. **Fork and adapt the target repository**
2. **Create an `environment.yml` file:**
   ```yaml
   name: model-env
   dependencies:
     - python=3.8
     - pytorch
     - librosa
     - your-dependencies
   ```

3. **Add a `main.py` entry point:**
   ```python
   import argparse
   
   def main():
       parser = argparse.ArgumentParser()
       parser.add_argument('-i', '--input', required=True)
       parser.add_argument('-o', '--output', required=True)
       args = parser.parse_args()
       
       # Your transcription logic here
       transcribe_audio(args.input, args.output)
   
   if __name__ == "__main__":
       main()
   ```

4. **Update `models.json`:**
   ```json
   {
     "values": [
       ["ModelName", "https://github.com/user/repo.git", "username", "token"]
     ]
   }
   ```

### Supported Models
Current evaluation includes:
- **MT3** - Google's Music Transformer
- **ReconVAT** - Variational autoencoder approach
- **Bytedance Piano Transcription** - CNN-based piano AMT
- **CREPE AMT** - Pitch estimation with transcription
- **Transkun AMT** - Transformer-based approach
- **Sound2MIDI Monophonic** - Single-voice transcription
- **Basic Pitch** - Spotify's open-source model
- **Madmom** - Signal processing toolkit
- **Melodia** - Melody extraction algorithm

## 🔧 Configuration

### SLURM Parameters
Default job configuration in `run.sh`:
```bash
#SBATCH -A standby
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=32
#SBATCH --time=03:59:00
```

### Google Drive Setup
1. Create a Google Cloud service account
2. Enable Drive API access
3. Share target folders with service account email
4. Download credentials as `service_account.json`

## 📊 Results and Analysis

### Output Structure
```
results/
├── ModelName/
│   ├── research_output/
│   │   ├── audio1.mid
│   │   ├── audio2.mid
│   │   └── ...
│   ├── details.txt          # Performance metrics
│   └── converted_scores/    # MusicXML outputs
```

### Performance Metrics
Each evaluation generates:
- **Average F-measure** across all test files
- **Average runtime** per audio file
- **Individual file scores** with detailed metrics
- **Instrument family accuracy** breakdown

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide for Python code
- Add docstrings to all functions
- Include error handling for file operations
- Test on small datasets before cluster deployment

## 🙏 Acknowledgments

- **Purdue University RCAC** for Gilbreth cluster access
- **AI for Musicians research group** at Purdue University
- **mir_eval developers** for transcription evaluation tools
- **Model authors** for open-source AMT implementations

## 📞 Support

For questions or issues:
- Open a GitHub issue
- Contact the AI for Musicians team

---

*This research is conducted as part of the AI for Musicians project at Purdue University, focusing on advancing automatic music transcription through comprehensive benchmarking and evaluation.*
