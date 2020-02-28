# https://github.com/MauriceBenink/python_pytest_base
FROM lib-test:latest
# docker build -t queryset_serializer_test
# docker run -it -v {project_root}:/package queryset_serializer_test

RUN pip3 install django==2.2.9 djangorestframework==3.9.2 pytest-django