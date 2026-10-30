# 브레이크타임 개발 환경 설정

확인일: 2026-10-30. 버전은 PyPI와 PyTorch 공식 공지 기준이며, **조합 설치는 실행 검증 안 됨**. 첫 설치 후 아래 "설치 확인"을 꼭 돌려 주세요.

## 한눈에 보기

| 항목 | 팀 공통 값 | 이유 |
|---|---|---|
| Python | 3.12 | torch 2.14 지원 범위(3.10~3.14) 안에서 안정적인 버전 |
| PyTorch | **2.14.0** (최신 2.15 아님) | 2.15부터 GTX 1060(Pascal) GPU 지원이 빠짐 |
| torchvision | 0.29.0 | torch 2.14.0과 짝 (PyTorch 공식 공지 기준) |
| CUDA 빌드 | **cu126** (CUDA 12.6) | 세 그래픽카드를 모두 지원하는 마지막 공식 빌드 |
| CUDA Toolkit 설치 | 필요 없음 | pip로 받는 torch에 CUDA 실행 파일이 포함됨 |
| NVIDIA 드라이버 | 각자 최신으로 업데이트 | CUDA 12.6 빌드를 돌리려면 드라이버가 충분히 최신이어야 함 |
| 가상환경 | conda, 이름 `breaktime` | 팀이 Anaconda 사용 |

## 그래픽카드별 정리

| 그래픽카드 | 세대 (Compute Capability) | torch 2.15 (cu13x) | torch 2.14 (cu126) |
|---|---|---|---|
| GTX 1060 | Pascal (6.1) | ❌ GPU 사용 불가 | ✅ |
| GTX 1660 SUPER | Turing (7.5) | ✅ | ✅ |
| RTX 3080 | Ampere (8.6) | ✅ | ✅ |

- **결론: 세 명 모두 torch 2.14.0 + cu126으로 통일한다.** 한 명만 다른 버전을 쓰면 "내 PC에선 되는데" 문제가 생긴다.
- "1060 Ti"라는 모델은 없어서 GTX 1060(3GB 또는 6GB)으로 가정했다. 어느 쪽이든 Pascal이라 결론은 같다.
- 1060과 1660 SUPER는 VRAM이 6GB 이하라서 작은 모델(`yolo11n` 등 n/s 크기)로 개발하고, 큰 모델 실험은 3080에서 한다.

## 설치 순서 (세 명 모두 동일)

```bash
# 1. 가상환경 만들기
conda create -n breaktime python=3.12
conda activate breaktime

# 2. PyTorch를 GPU(CUDA 12.6) 빌드로 먼저 설치
pip install torch==2.14.0 torchvision==0.29.0 --index-url https://download.pytorch.org/whl/cu126

# 3. 나머지 라이브러리 설치
pip install -r requirements-dev.txt
```

2번을 3번보다 **먼저** 해야 한다. 순서가 바뀌면 ultralytics가 PyPI의 최신 torch(2.15)를 끌어와서 1060에서 GPU가 안 잡힌다.

## 설치 확인

```bash
nvidia-smi   # 드라이버와 그래픽카드가 보이는지
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 기대 결과: 2.14.0+cu126 True <내 그래픽카드 이름>
```

`False`가 나오면 NVIDIA 드라이버를 최신으로 업데이트하고 다시 확인한다.

## 가상환경에 들어가는 것

| 파일 | 내용 | 누가 쓰나 |
|---|---|---|
| (2단계 명령) | torch, torchvision | A (YOLO가 내부에서 사용) |
| `requirements.txt` | ultralytics, lap, opencv-python, pyyaml, fastapi, uvicorn, python-multipart, pydantic | 전체 |
| `requirements-dev.txt` | pytest, black, ruff (+ requirements.txt) | 개발할 때 전체 |

- numpy 등은 위 라이브러리가 알아서 함께 설치하므로 따로 적지 않았다.
- 라이브러리를 추가한 사람은 버전을 고정(`==`)해서 파일에 적고 팀에 알린다.

## 근거
- [PyTorch 공지: 2.15부터 CUDA 12.6 빌드 중단 (Maxwell/Pascal/Volta 제외)](https://dev-discuss.pytorch.org/t/notice-cuda-12-6-wheels-will-no-longer-be-published-from-pytorch-2-15-drops-maxwell-pascal-volta/3432)
- [PyTorch 2.15 CUDA 지원 매트릭스 RFC](https://github.com/pytorch/pytorch/issues/190385)
- 라이브러리 최신 버전과 지원 파이썬: PyPI에서 확인 (2026-10-30)
