def test_every_view(client,archived):
    for key,label in [('intake','同号日志矛盾'),('registry','有效窗 UTC'),('custody','查验调位回放'),
                      ('exposure','门信号抖动'),('capacity','件数守恒'),('history','复算原件'),('certificate','下载整组证据')]:
        response = client.get(f'/view/{key}?receipt={archived["id"]}')
        assert response.status_code == 200 and label in response.get_data(as_text=True)


def test_home_renders_real_track(client):
    html = client.get('/').get_data(as_text=True)
    assert '货批事件泳道' in html and 'data-lot="F03"' in html
    assert '槽位缺证 · X9 · 00:10:00' in html


def test_failed_api_has_reason(client):
    response = client.get('/api/observe/custody?sample=missing')
    assert (response.status_code,response.json['code']) == (404,'NO_SAMPLE')


def test_late_seal_has_timeline_marker(client):
    html = client.get('/view/custody').get_data(as_text=True)
    assert 'class="marker late"' in html and 'SEAL · 00:18:00 · 原行 7 · 迟补' in html


def test_registry_runs_independently_of_bad_window(client):
    from app.parcels import load_example
    pack = dict(load_example('dirty'), window='false')
    assert client.post('/api/observe/registry', json=pack).json['counts']['revisions'] == 4
    assert client.post('/api/observe/custody', json=pack).json['code'] == 'WINDOW'
    assert client.get('/api/receipts').json['count'] == 0
