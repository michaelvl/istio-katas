FROM python:3.9.0-buster AS builder

RUN pip install grpcio-tools

COPY app-grpc /usr/src/app-grpc/

RUN cd /usr/src/app-grpc && python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. age.proto
RUN cd /usr/src/app-grpc && python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. name.proto

FROM python:3.9.0-buster

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

COPY app /usr/src/app/

COPY app-grpc /usr/src/app-grpc/
COPY --from=builder /usr/src/app-grpc/age_pb2.py  /usr/src/app-grpc/age_pb2_grpc.py  /usr/src/app-grpc/
COPY --from=builder /usr/src/app-grpc/name_pb2.py /usr/src/app-grpc/name_pb2_grpc.py /usr/src/app-grpc/

EXPOSE 5000

ENTRYPOINT ["python"]
CMD ["/usr/src/app/sentences.py"]
