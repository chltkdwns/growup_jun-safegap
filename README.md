# SafeGap

블랙박스 영상만으로 앞차와의 거리를 추정하고, 충돌 위험이 있으면 미리 경고해 주는 전방 충돌 경고 서비스입니다.

## 주요 기능
- 블랙박스 영상 업로드
- 앞차 검출 및 추적 (YOLO)
- 앞차까지 거리 추정 (Depth Anything V2)
- 충돌까지 남은 시간(TTC) 계산 및 단계별 경고 (주의 · 경고 · 위험)

## 기술 스택
| 구분 | 기술 |
|---|---|
| 프론트엔드 | Next.js · TypeScript · Tailwind CSS |
| 백엔드 | FastAPI (Python) |
| AI 모델 | YOLOv8 · Depth Anything V2 |
| DB | PostgreSQL |
| 배포 | GitHub · Vercel |

## 폴더 구조
```
frontend/   # Next.js 화면
backend/    # FastAPI 서버
model/      # 차량 검출 · 거리 추정 · TTC 계산
```

## 개발 기간
2026.10.28 ~ 2026.11.04

## 팀원
| 이름 | 역할 |
|---|---|
| | 프론트엔드 |
| | 백엔드 · 깃 관리 |
| | AI 모델 |

> 개발 규칙과 실행 방법은 [CONTRIBUTING.md](./CONTRIBUTING.md)를 참고하세요.