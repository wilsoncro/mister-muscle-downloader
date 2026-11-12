"""v5.3.10 regression: service-specific login popup and Instagram session reuse."""
import ast
import re
import tempfile
import time
import types
import urllib.parse
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE=(HERE/'mister_muscle_qt.py').read_text(encoding='utf-8')
SETUP=(HERE/'MisterMuscle_Setup.iss').read_text(encoding='utf-8')
assert "APP_VERSION = '5.3.10'" in SOURCE
assert '#define MyAppVersion "5.3.10"' in SETUP
TREE=ast.parse(SOURCE)

def extract(name,class_name=None,namespace=None):
    members=TREE.body
    if class_name:
        cls=next(n for n in TREE.body if isinstance(n,ast.ClassDef) and n.name==class_name)
        members=cls.body
    node=next(n for n in members if isinstance(n,ast.FunctionDef) and n.name==name)
    mod=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    env=dict(namespace or {})
    exec(compile(mod,'<login regression>','exec'),env)
    return env[name]

host=extract('_restricted_media_host',namespace={'urllib':urllib})
saved_args=extract('_instagram_saved_cookie_args',namespace={
    '_restricted_media_host':host,'Path':Path})
notice=extract('_restricted_media_notice')

class MockBox:
    Information=1
    AcceptRole=2
    RejectRole=3
    ActionRole=4
    dialogs=[]
    accept_next=True
    def __init__(self,parent):
        self.parent=parent
        self._buttons=[]
        self._chosen=None
        self.title=''
        self.body=''
        MockBox.dialogs.append(self)
    def setIcon(self,icon):self.icon=icon
    def setWindowTitle(self,title):self.title=title
    def setText(self,text):self.body=text
    def setInformativeText(self,text):self.info=text
    def addButton(self,label,role):
        button=object()
        self._buttons.append((label,role,button))
        return button
    def exec(self):
        self._chosen=self._buttons[0][2] if MockBox.accept_next else self._buttons[-1][2]
    def clickedButton(self):return self._chosen

class Browser:
    opened=[]
    @classmethod
    def openUrl(cls,url):
        cls.opened.append(url)
        return True

class MockHotstarLoginDialog:
    shown=[]
    accepted=True
    def __init__(self,url,parent):
        self.url=url;self.parent=parent
        self.shown.append(url)
    def exec(self):
        return 1 if self.accepted else 0

pending=[]
timer=types.SimpleNamespace(singleShot=lambda delay,callback:pending.append((delay,callback)))
popup=extract('_offer_media_login_popup','Main',namespace={
    '_restricted_media_notice':notice,'_restricted_media_host':host,
    'QMessageBox':MockBox,'HotstarLoginDialog':MockHotstarLoginDialog,
    'QDialog':types.SimpleNamespace(DialogCode=types.SimpleNamespace(Accepted=1)),
    'QDesktopServices':Browser,'QUrl':lambda url:url,
    'QTimer':timer,'time':time,'WEB_ENGINE_AVAILABLE':True,
    'extract_media_links':lambda text:[text] if text else [],
})

class FakeUrlField:
    def __init__(self,url):self.url=url
    def toPlainText(self):return self.url

class Page:
    _offer_media_login_popup=popup
    def __init__(self,url,logged_in=True):
        self.urls=FakeUrlField(url)
        self._media_login_popup_recent={}
        self.login_calls=0
        self.inspect_calls=0
        self.preview_calls=0
        self.logged_in=logged_in
        self._hotstar_browser_session=None
        self._restricted_download_retry=None
        self.queue=[]
        self.queue_updated=False
    def log(self,level,source,message):
        self.last_log=(level,source,message)
    def persist_session(self):pass
    def refresh_queue(self):self.queue_updated=True
    def run_next(self):self.retry_called=True
    def login_instagram(self):
        self.login_calls+=1
        return self.logged_in
    def inspect_link(self):self.inspect_calls+=1
    def preview_link(self):self.preview_calls+=1

HOTSTAR='ERROR: [hotstar] 1000066865: This video is only available for registered users.'
INSTAGRAM='ERROR: [Instagram] Please log in to view this post.'

def test_host_identification():
    assert host('https://www.instagram.com/reel/abc','')=='instagram'
    assert host('https://www.hotstar.com/in/shows/sample','')=='hotstar'
    assert host('https://www.jiohotstar.com/shows/sample','')=='hotstar'
    assert host('https://unknown.invalid/watch',HOTSTAR)=='hotstar'
    assert host('https://instagram.com.evil.example/foo','')=='other'
    assert host('https://hotstar.com.evil.example/foo','')=='other'
    assert host('https://other.example/video','')=='other'
    assert notice(INSTAGRAM) is not None
    assert notice(HOTSTAR) is not None
    assert notice('A random FFmpeg conversion failure') is None
    print('PASS authentic provider identification, fake-domain rejection, sign-in classification')

def test_cookies_only_on_instagram():
    hotstar=extract('_hotstar_saved_cookie_args',namespace={
        '_restricted_media_host':host,'Path':Path})
    with tempfile.TemporaryDirectory() as td:
        h_file=Path(td)/'hotstar_cookies.txt'
        assert hotstar('https://www.hotstar.com/watch/123',h_file)==[]
        h_file.write_text('# Netscape HTTP Cookie File\n.hotstar.com\tTRUE\t/\tTRUE\t4102444800\tsession\t123\n',encoding='utf-8')
        assert hotstar('https://www.hotstar.com/watch/123',h_file)==['--cookies',str(h_file)]
        assert hotstar('https://www.jiohotstar.com/watch/123',h_file)==['--cookies',str(h_file)]
        assert hotstar('https://www.instagram.com/reel/abc',h_file)==[]
        assert hotstar('https://hotstar.com.evil.example/fake',h_file)==[]
        assert hotstar('https://www.hotstar.com/watch/123',None)==[]
    assert "class HotstarLoginDialog(QDialog):" in SOURCE
    assert "dialog=HotstarLoginDialog(url,self)" in SOURCE
    assert "def login_hotstar(self)" in SOURCE and "def logout_hotstar(self)" in SOURCE
    assert "profile.cookieStore().deleteAllCookies()" in SOURCE
    assert "'Log into Hotstar in app'" in SOURCE
    assert 'args+=self._media_cookie_args(self.current_url)' in SOURCE
    assert "*self._media_cookie_args(links[0])" in SOURCE
    assert "*self._media_cookie_args(url)" in SOURCE
    with tempfile.TemporaryDirectory() as td:
        cookie_file=Path(td)/'instagram_cookies.txt'
        assert saved_args('https://www.instagram.com/reel/abc',cookie_file)==[]
        cookie_file.write_text('# Netscape HTTP Cookie File\n',encoding='utf-8')
        assert saved_args('https://www.instagram.com/reel/abc',cookie_file)==['--cookies',str(cookie_file)]
        assert saved_args('https://www.hotstar.com/watch/123',cookie_file)==[]
        assert saved_args('https://instagram.com.evil.example/a',cookie_file)==[]
    assert "*self._media_cookie_args(links[0])" in SOURCE
    assert "def login_instagram(self)" in SOURCE
    assert "return True" in SOURCE[SOURCE.index('    def login_instagram(self)'):SOURCE.index('    def logout_instagram(self)')]
    print('PASS explicit saved Instagram cookies used for Inspect/Preview, never sent to Hotstar')

def test_hotstar_popup():
    MockBox.dialogs.clear();Browser.opened.clear();pending.clear()
    MockHotstarLoginDialog.shown.clear()
    url='https://www.hotstar.com/in/shows/sample'
    page=Page(url)
    page._offer_media_login_popup('PREVIEW',HOTSTAR,url)
    assert len(MockBox.dialogs)==1
    d=MockBox.dialogs[-1]
    assert d.title=='Hotstar sign-in required'
    assert d._buttons[0][0]=='Log into Hotstar in app'
    assert d._buttons[1][0]=='Open Hotstar website'
    assert MockHotstarLoginDialog.shown==[url]
    assert page.login_calls==0 and Browser.opened==[]
    assert len(pending)==1
    pending.pop()[1]()
    assert page.preview_calls==1
    page._offer_media_login_popup('INSPECT',HOTSTAR,url)
    assert len(MockBox.dialogs)==1, 'Duplicate Inspect/Preview errors should not open multiple dialogs'
    print('PASS Hotstar opens its embedded official-login dialog and retries preview')

def test_hotstar_download_retry():
    MockBox.dialogs.clear();Browser.opened.clear();pending.clear()
    url='https://www.hotstar.com/in/watch/1000066865'
    p=Page(url)
    p._restricted_download_retry=(url,0,'Best available','mp4')
    p._offer_media_login_popup('DOWNLOAD',HOTSTAR,url)
    assert MockHotstarLoginDialog.shown[-1]==url
    assert len(p.queue)==1
    assert p.queue[0][0]==url and p.queue_updated
    assert p._restricted_download_retry is None
    pending.pop()[1]()
    assert p.retry_called
    assert p.login_calls==0
    print('PASS Hotstar download can retry inside app after embedded login')

def test_instagram_existing_login_and_retry():
    MockBox.dialogs.clear();Browser.opened.clear();pending.clear()
    url='https://www.instagram.com/reel/sample'
    page=Page(url)
    page._offer_media_login_popup('INSPECT',INSTAGRAM,url)
    assert MockBox.dialogs[-1].title=='Instagram sign-in required'
    assert MockBox.dialogs[-1]._buttons[0][0]=='Log into Instagram'
    assert page.login_calls==1 and len(pending)==1
    pending.pop()[1]()
    assert page.inspect_calls==1
    assert Browser.opened==[]
    page2=Page(url)
    page2._offer_media_login_popup('PREVIEW',INSTAGRAM,url)
    assert page2.login_calls==1 and len(pending)==1
    pending.pop()[1]()
    assert page2.preview_calls==1
    page3=Page(url,logged_in=False)
    page3._offer_media_login_popup('PREVIEW',INSTAGRAM,url)
    assert page3.login_calls==1 and len(pending)==0
    page4=Page(url)
    page4._offer_media_login_popup('INSPECT',INSTAGRAM,url)
    page4.urls.url='https://www.instagram.com/reel/other'
    pending.pop()[1]()
    assert page4.inspect_calls==0, 'Do not retry a link user has changed'
    print('PASS reuse existing Instagram login and retry the same URL on success only')

def test_cancel_and_genuine_errors():
    MockBox.dialogs.clear();Browser.opened.clear();pending.clear()
    MockBox.accept_next=False
    try:
        p=Page('https://www.hotstar.com/watch/abc')
        p._offer_media_login_popup('INSPECT',HOTSTAR,p.urls.url)
        assert Browser.opened==[]
        assert p.login_calls==0 and pending==[]
    finally:
        MockBox.accept_next=True
    print('PASS cancel never opens URLs or login windows')


def test_hotstar_cookie_capture():
    """Website cookie data, never passwords or cross-provider cookies, is exported."""
    import os
    class Label:
        def __init__(self):self.text=''
        def setText(self,v):self.text=v
    class Cookie:
        def __init__(self,domain,name=b'sessionid',value=b'authorized-token'):
            self._domain=domain;self._name=name;self._value=value
        def domain(self):return self._domain
        def name(self):return self._name
        def value(self):return self._value
        def path(self):return '/'
        def isSecure(self):return True
        def isSessionCookie(self):return False
        def expirationDate(self):
            return types.SimpleNamespace(toSecsSinceEpoch=lambda:4102444800)
    with tempfile.TemporaryDirectory() as td:
        output=Path(td)/'hotstar_cookies.txt'
        namespace={'time':time,'os':os,'HOTSTAR_COOKIES':output}
        record=extract('_on_cookie','HotstarLoginDialog',namespace)
        finish=extract('_finish_login','HotstarLoginDialog',namespace)
        host_login=types.SimpleNamespace(_cookies={},_status=Label(),_saved=False,
            accept=lambda:None)
        record(host_login,Cookie('www.hotstar.com'))
        record(host_login,Cookie('.jiohotstar.com',b'auth',b'active-session'))
        record(host_login,Cookie('.instagram.com',b'ig_session',b'must-not-appear'))
        record(host_login,Cookie('attacker.com',b'malicious',b'must-not-appear'))
        assert len(host_login._cookies)==2
        finish(host_login)
        assert output.is_file() and host_login._saved
        written=output.read_text(encoding='utf-8')
        assert 'hotstar.com' in written and 'jiohotstar.com' in written
        assert 'instagram.com' not in written
        assert 'attacker.com' not in written
        assert 'must-not-appear' not in written
        assert 'authorized-token' in written
        assert 'Netscape HTTP Cookie File' in written
    print('PASS Hotstar embedded session exports only service cookies, no cross-host data')

if __name__=='__main__':
    test_host_identification()
    test_cookies_only_on_instagram()
    test_hotstar_popup()
    test_hotstar_download_retry()
    test_instagram_existing_login_and_retry()
    test_cancel_and_genuine_errors()
    test_hotstar_cookie_capture()
    from test_restricted_media_539 import (
        test_access_classification,test_four_independent_users,test_unknown_error_still_reported_once)
    test_access_classification()
    test_four_independent_users()
    test_unknown_error_still_reported_once()
    from test_car_multimedia_538 import test_compatibility
    test_compatibility()
    from test_windows_cleanup_537 import test_temporary_locks,test_http_disconnect
    test_temporary_locks()
    test_http_disconnect()
    from test_separate_audio_markers_536 import markers_test,ffmpeg_test
    markers_test()
    ffmpeg_test()
    from test_full_waveform_and_cuts_535 import _check_waveform
    _check_waveform()
    print('PASS v5.3.10 and all previous Windows/media regressions')
