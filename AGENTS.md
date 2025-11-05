# Repository Guidelines


使用中文回答我

## Project Structure & Module Organization
- Core research code lives in `time_moe/` (datasets, models, runner, trainer). Keep new algorithms here so they are reachable through `main.py` and `torch_dist_run.py`.
- `TimeMoE-50M/` holds the default checkpoint and configs, while `data/` stores benchmark inputs and `figures/` contains paper assets. Do not commit raw datasets outside `data/`.
- `timemoe_service/` packages the FastAPI layer; mirror the existing `api/`, `core/`, `services/`, `utils/` layout when extending the service.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` (root) or `pip install -r timemoe_service/requirements.txt` (service) to sync dependencies.
- `python main.py -d <data_path> --output_path logs/time_moe` starts single-node training or fine-tuning; add `--from_scratch` for fresh initialisation.
- `python torch_dist_run.py main.py -d <data_path>` wraps distributed launches; ensure `MASTER_ADDR`, `MASTER_PORT`, `WORLD_SIZE`, and `RANK` are exported.
- `python run_eval.py -d data/ETT-small/ETTh1.csv -p 96` reproduces the ETTh1 benchmark, while `bash run_timemoe.sh` spins up the Ascend NPU smoke test. For service work, run `uvicorn app.main:fastapi_app --host 0.0.0.0 --port 8000`.

## Coding Style & Naming Conventions
- Target Python 3.10+, 4-space indentation, and PEP 8 compliant `snake_case`. Prefer type hints on public functions, especially loaders and service endpoints.
- Keep configs in JSON/YAML with lowercase filenames (`configuration_time_moe.py` exposes strongly typed accessors). Document tensor shapes in comments when they are not obvious.

## Testing Guidelines
- Execute `python test_timemoe.py` (CPU/GPU) or `python test_timemoe_mirror.py` (NPU) before pushing hardware-related changes; run `python verify_npu.py` if unsure about device availability.
- Treat `python run_eval.py ...` as a regression test and include the command and outcome in PR notes.
- Populate `timemoe_service/tests/` with `pytest` cases using `TestClient` whenever API routes change.

## Commit & Pull Request Guidelines
- Write concise, imperative subjects and reference issues or PR IDs when relevant (`Update README.md (#87)` is the current pattern).
- Consolidate work into review-ready commits; PR descriptions should list motivation, key commands run, and any dataset or service configuration requirements.
- Avoid committing large weight files—store them under `data/models/` or reference Hugging Face IDs via `--model_path`. Note new environment variables or ports in the PR body.

## Security & Configuration Tips
- Keep secrets out of source; place them in ignored `.env` files and follow the samples in `timemoe_service/config/`.
- Cache large checkpoints locally but never commit them; document download steps so teammates can reproduce your setup.


