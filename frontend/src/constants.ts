// 경고 단계 이름·색은 여기 한곳에서만 정한다. 판정(어느 단계인지)은 서버가 level로 내려준다.
export type Level = '정상' | '주의' | '경고' | '위험'

// 낮은 단계부터 높은 단계 순서. 단계가 올랐는지 비교할 때 인덱스로 쓴다.
export const LEVEL_ORDER: Level[] = ['정상', '주의', '경고', '위험']

// 단계별 표시 문구와 색
export const LEVELS: Record<Level, { ko: string; en: string; color: string }> = {
  정상: { ko: '안전', en: 'SAFE', color: '#3cc983' },
  주의: { ko: '주의', en: 'CAUTION', color: '#f3c744' },
  경고: { ko: '경고', en: 'WARNING', color: '#ff8b3d' },
  위험: { ko: '위험', en: 'DANGER', color: '#ff4b55' },
}

// 서버가 보내는 박스 좌표(lead_box_px)의 기준 화면 크기(px). 오버레이를 이 크기로 그려 영상 크기에 맞춰 늘린다.
export const FRAME_W_PX = 1920
export const FRAME_H_PX = 1080

// 상대 속도는 서버가 m/s로 보내고 화면에는 km/h로 보여 준다
export const MS_TO_KMH = 3.6

// 내 속도 슬라이더 범위(km/h). 처음 값은 서버 mock의 기본 속도(MOCK_SPEED_KMH)와 같아야 한다.
export const SPEED_MIN_KMH = 30
export const SPEED_MAX_KMH = 130
export const SPEED_STEP_KMH = 5
export const DEFAULT_SPEED_KMH = 50

// 경고가 나온 이유. 서버(schemas.py의 EventType)와 같은 이름이어야 한다.
export type EventType = 'gap_short' | 'cut_in' | 'hard_brake'

// 이유별 배너 문구
export const EVENTS: Record<EventType, string> = {
  gap_short: '안전거리가 부족해요',
  cut_in: '옆 차가 끼어들었어요',
  hard_brake: '앞차가 급정거했어요',
}

// ---- 실시간(live) 모드: 폰/웹캠 프레임을 서버로 보내 분석한다 ----
// 서버 config.yaml의 api.live_fps와 같게 둔다 (B의 TTC 창이 이 값으로 계산된다)
export const LIVE_FPS = 15
// 서버로 보낼 프레임의 "긴 변"(px). 폰을 가로로 들든 세로로 들든 긴 변을 이 길이로 줄여 보내서, 서버가 구한 초점거리가 항상 같다.
// 클수록 정확하지만 업로드가 커진다 (640px, 품질 0.6에서 약 43KB/장 = 5Mbps). 초점거리는 서버가 정한다(config api.live_hfov_deg)
export const LIVE_SEND_LONG_PX = 640
export const LIVE_JPEG_QUALITY = 0.6
// 서버로 가는 중인 데이터가 이 크기(바이트)를 넘으면 새 프레임을 보내지 않는다 (네트워크가 느릴 때 지연이 쌓이지 않게)
export const LIVE_MAX_BUFFERED_BYTES = 200_000

// 서버가 알려 준 영상 위치와 실제 영상 재생 위치가 이만큼(초) 넘게 벌어지면 영상 위치를 서버에 맞춘다.
// 너무 작으면 되감기가 잦아 끊겨 보이고, 너무 크면 박스가 영상보다 앞서거나 뒤처져 보인다.
export const VIDEO_SYNC_TOLERANCE_S = 0.15

// 배너 문구를 최소로 유지하는 시간(ms). 순간적으로 스쳐 지나가는 문구도 읽을 수 있게 한다.
export const EVENT_HOLD_MS = 2000
