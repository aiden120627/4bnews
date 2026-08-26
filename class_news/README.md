# 📰 우리반 뉴스

관리자만 뉴스를 올리고, 학생들은 뉴스와 이미지를 보고 좋아요만 누를 수 있는 반 전용 뉴스 웹입니다.

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 `http://127.0.0.1:8000` 접속.

관리자 페이지: `http://127.0.0.1:8000/admin`

기본 관리자 키: `100525`

## Render 배포

`render.yaml`이 포함되어 있어서 GitHub에 올린 뒤 Render에서 해당 저장소를 선택하면 설정을 불러올 수 있습니다.

Render 환경변수 `ADMIN_KEY`를 `100525`로 설정하세요. `DATABASE_PATH`와 디스크 설정은 `render.yaml`에 넣어 두었습니다.

### 참고

이미지는 현재 Render 디스크의 `/var/data`가 아닌 프로젝트의 `uploads` 폴더에 저장됩니다. 영구 이미지 저장이 필요하면 나중에 Cloudinary 같은 외부 이미지 스토리지로 교체하는 것을 권장합니다. DB는 Render 디스크에 저장되도록 설정되어 있습니다.
