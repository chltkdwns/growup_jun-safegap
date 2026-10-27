# model

SafeGap 분석 파이프라인 (YOLOv8 · Depth Anything V2 · OpenCV)

## 처리 순서
1. 영상에서 프레임 추출, 본넷 영역 제거
2. YOLO로 차량 검출 · 추적
3. 내 차선에서 가장 가까운 차를 앞차로 선택
4. Depth Anything V2로 앞차까지 거리 추정
5. 거리 변화로 TTC 계산 → 경고 단계 결정 (주의 · 경고 · 위험)

## 주의
- 모델 가중치(*.pt)와 영상(*.mp4)은 용량 때문에 깃에 올리지 않기