FROM python:3.9
ENV WEB3_URL=http://localhost8024
RUN pip install pipenv
COPY . /tmp/myapp
RUN cd /tmp/myapp && pipenv install
CMD cd /tmp/myapp && pipenv run python -m agent ${WEB3_URL} 3000
