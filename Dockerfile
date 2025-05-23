# 1. Miniconda 베이스 이미지
FROM continuumio/miniconda3:latest

# 2. conda 환경이 설치될 경로를 PATH에 추가
ENV CONDA_ENV_NAME=tts-env
ENV PATH=/opt/conda/envs/$CONDA_ENV_NAME/bin:$PATH

# 3. 환경 정의 파일 복사 및 conda env 생성
COPY environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml -n $CONDA_ENV_NAME \
    && conda clean -afy

# 4. 앱 코드 복사
WORKDIR /app
COPY . /app

# 5. 외부에 개방할 포트
EXPOSE 8000

# 6. 컨테이너 시작 시 uvicorn 실행
#    --reload 옵션은 개발용이며, 프로덕션에서는 제거하는 걸 권장합니다.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

