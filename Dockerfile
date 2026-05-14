FROM alpine:3.23.4

RUN echo "У нас два докерфайла, а джоба в пайплайне ищет один с названием 'Dockerfile'. Вынужденная мера"

CMD ["/bin/true"]
