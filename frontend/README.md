# frontend

SafeGap 웹 화면 (Next.js · TypeScript · Tailwind CSS)

## 담당 기능
- 블랙박스 영상 업로드 화면
- 분석 결과 영상 재생 + 앞차 박스 · 거리 · TTC 표시
- 단계별 경고 표시 (주의 · 경고 · 위험, 색 · 소리)
- (선택) 분석 기록 조회

## 예정 구조
```
app/          # 페이지
components/   # 영상 플레이어, 경고 배너 등
lib/api.ts    # 백엔드 API 호출
```