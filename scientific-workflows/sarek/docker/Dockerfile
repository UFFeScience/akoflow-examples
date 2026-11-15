FROM hub.akoflow.com/akoflow-examples/rnaseq@sha256:edb949835c96cf793c9ef21009d583bb7b93cb845df784ac0e5221d1b9b23acb AS runtime
COPY upstream /app/upstream/sarek
COPY prepare-envs.sh /tmp/prepare-sarek-envs.sh
RUN bash /tmp/prepare-sarek-envs.sh
WORKDIR /app
COPY prepare-local-envs.sh /tmp/prepare-sarek-local-envs.sh
RUN bash /tmp/prepare-sarek-local-envs.sh

RUN env -u NXF_OFFLINE nextflow plugin install nf-core-utils@0.4.0 && env -u NXF_OFFLINE nextflow plugin install nf-fgbio@1.0.0 && env -u NXF_OFFLINE nextflow plugin install nf-prov@1.7.0

FROM runtime AS workflow
COPY scripts /app/scripts
COPY data /app/data
COPY config /app/config
COPY workflow.json /app/workflow.json
ENV NXF_OFFLINE=true
