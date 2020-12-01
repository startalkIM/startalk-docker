import json
import sys
import telnetlib
import urllib
import urllib.request

NAV_URL = "https://qim.qunar.com/package/static/qtalk/nav?p=pc"

HOST = "172.17.100.18"
user = "test"
password = "123456"


def command(con, flag, str_=""):
    data = con.read_until(flag.encode())
    print(data.decode(errors='ignore'))
    con.write(str_.encode() + b"\n")
    return data


def load_navigation(url):
    try:
        print('startalk: begin to test navigation, url is %s.' % url)
        f = urllib.request.urlopen(url)
        response_string = f.read().decode('utf-8')
        print('startalk: navigation test ok.')
        return json.loads(response_string)
    except:
        raise


class StartalkConnectionError(object):
    pass


def check_xmpp_connection(json_object):
    ip = ''
    port = 0
    if json_object is not None:
        base_address = json_object['baseaddess']

        ip = base_address['xmpp']
        port = base_address['protobufPcPort']

        telnet = telnetlib.Telnet()
        telnet.open(ip, port)
        telnet.close()
        print('startalk tcp: %s:%d done.' % (ip, port))
        return
    raise StartalkConnectionError('check_xmpp_connection failed on %s - %d' % (ip, port))


def main(argv):
    # try:
    json_object = load_navigation(NAV_URL)
    check_xmpp_connection(json_object)

    # except:
    #     print('导航获取失败: %s' % NAV_URL)
    #
    # if json_object is not None:
    #     base_address = json_object['baseaddess']
    #
    #     ip = base_address['xmpp']
    #     port = base_address['protobufPcPort']
    #
    #     port = 456
    #
    #     telnet = telnetlib.Telnet()
    #     telnet.open(ip, port)
    #
    #     print('ip is %s' % ip)
    #
    # tn = telnetlib.Telnet(HOST)
    # command(tn, "login: ", user)
    # if password:
    #     command(tn, "Password: ", password)
    # command(tn, "$", "ls")
    # command(tn, "$", " exit")
    # command(tn, "$", "")
    # tn.close()


pass

if __name__ == '__main__':
    main(sys.argv)
