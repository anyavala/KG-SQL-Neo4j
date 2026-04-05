FROM python:3.13-slim
WORKDIR /code
COPY src ./src/
COPY pyproject.toml README.md ./
RUN pip install .
RUN mkdir -p /root/.biokb/brenda
CMD ["fastapi", "run","src/biokb_brenda/api/main.py"]