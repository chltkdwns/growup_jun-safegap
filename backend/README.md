# backend

SafeGap API 서버 (FastAPI · PostgreSQL)

## 담당 기능
- 영상 업로드 받기
- model/ 의 분석 파이프라인 실행
- 분석 결과 (프레임별 박스 · 거리 · TTC · 경고 단계) 반환
- 분석 기록 · 경고 이벤트 DB 저장

## 예정 API
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /api/videos | 영상 업로드 |
| GET | /api/videos/{id}/result | 분석 결과 조회 |
| GET | /api/videos | 분석 기록 목록 |