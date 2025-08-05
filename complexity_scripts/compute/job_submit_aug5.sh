# XMIDI (largest - needs yunglu-k with 24-hour limit)
sbatch -A yunglu-k --partition=gilbreth-k --time=24:00:00 --cpus-per-task=60 --nodes=1 --gres=gpu:1 --job-name=complexity_xmidi --output=logs/complexity_xmidi_%j.out --error=logs/complexity_xmidi_%j.err run_complexity_analysis.sh xmidi

# NESMDB (medium - needs 8 hours)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=48 --nodes=1 --gres=gpu:1 --job-name=complexity_nesmdb --output=logs/complexity_nesmdb_%j.out --error=logs/complexity_nesmdb_%j.err run_complexity_analysis.sh nesmdb

# SLAKH2100 (medium - needs 6 hours)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=32 --nodes=1 --gres=gpu:1 --job-name=complexity_slakh --output=logs/complexity_slakh_%j.out --error=logs/complexity_slakh_%j.err run_complexity_analysis.sh slakh2100

# MAESTRO (small - 4 hours OK)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=16 --nodes=1 --gres=gpu:1 --job-name=complexity_maestro --output=logs/complexity_maestro_%j.out --error=logs/complexity_maestro_%j.err run_complexity_analysis.sh maestro

# POP909 (small - 4 hours OK)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=16 --nodes=1 --gres=gpu:1 --job-name=complexity_pop909 --output=logs/complexity_pop909_%j.out --error=logs/complexity_pop909_%j.err run_complexity_analysis.sh pop909

# MSMD (small - 4 hours OK)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=8 --nodes=1 --gres=gpu:1 --job-name=complexity_msmd --output=logs/complexity_msmd_%j.out --error=logs/complexity_msmd_%j.err run_complexity_analysis.sh msmd

# AAM (small - 4 hours OK)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=32 --nodes=1 --gres=gpu:1 --job-name=complexity_aam --output=logs/complexity_aam_%j.out --error=logs/complexity_aam_%j.err run_complexity_analysis.sh aam

# BIMMUDA (small - 4 hours OK)
sbatch -A standby --partition=gilbreth-standby --time=04:00:00 --cpus-per-task=8 --nodes=1 --gres=gpu:1 --job-name=complexity_bimmuda --output=logs/complexity_bimmuda_%j.out --error=logs/complexity_bimmuda_%j.err run_complexity_analysis.sh bimmuda