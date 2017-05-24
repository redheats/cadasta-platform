from tasks.celery import app


@app.task(name='export.hello')
def test(name='yes'):
    print(name)
