# 우리반 뉴스

관리자만 뉴스 작성/수정/삭제를 할 수 있고, 학생은 뉴스에 좋아요만 누를 수 있는 간단한 반 뉴스 사이트입니다.

## 기본 관리자 키
`100525`

실제 배포에서는 Render Environment Variable `ADMIN_KEY`에 설정하세요.

## Render 배포
ZIP을 풀어서 **파일과 폴더를 GitHub 저장소 최상위**에 올립니다.

정상 구조:

```text
main.py
requirements.txt
render.yaml
static/
uploads/
```

따라서 Render의 **Root Directory는 비워둡니다.**

- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

`render.yaml`을 사용하면 `/var/data` 영구 디스크, `DATA_DIR` 설정 등을 같이 적용할 수 있습니다. Render 대시보드에서 디스크 설정이 자동 적용되지 않으면 Web Service의 Disks에서 `/var/data` 디스크를 추가하세요.

## 관리자 페이지
배포 후 `/admin` 접속 → 관리자 키 `100525` 입력.
