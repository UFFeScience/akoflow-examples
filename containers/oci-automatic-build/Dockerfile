FROM alpine@sha256:469c9ea410b9215eaee7976ba6c0639039b444be8e5d638f7abbada189971eb2
LABEL org.opencontainers.image.title="Akoflow automatic OCI build demo"
RUN printf 'Akoflow built this OCI image automatically before execution.\n' > /image-build-proof.txt
CMD ["sh", "-c", "cat /image-build-proof.txt"]
