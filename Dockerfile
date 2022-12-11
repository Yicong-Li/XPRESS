FROM python:3.9-slim

RUN apt-get update && \
    apt-get install -y git
    
RUN apt-get install -y gcc
RUN apt-get install -y g++

RUN groupadd -r evaluator && useradd -m --no-log-init -r -g evaluator evaluator

RUN mkdir -p /opt/evaluation /input /output \
    && chown evaluator:evaluator /opt/evaluation /input /output

USER evaluator
WORKDIR /opt/evaluation

ENV PATH="/home/evaluator/.local/bin:${PATH}"

RUN python -m pip install --user -U pip

COPY --chown=evaluator:evaluator ground-truth /opt/evaluation/ground-truth

COPY --chown=evaluator:evaluator requirements.txt /opt/evaluation/

RUN python -m pip install --user -rrequirements.txt

RUN python -m pip install --user git+https://github.com/funkelab/funlib.evaluate@d2852b3#egg=funlib.evaluate

COPY --chown=evaluator:evaluator evaluation.py /opt/evaluation/

ENTRYPOINT "python" "-m" "evaluation"
