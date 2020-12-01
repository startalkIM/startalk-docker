

local http_responce = {}

function http_responce.okResponce(data)
    return http_responce.okResponce3(0,"",data);
end

function http_responce.okResponce2(errmsg,data)
    return http_responce.okResponce3(0,errmsg,data);
end


function http_responce.rawResponce(data)
    local json = require "cjson"
    return json.encode(data);
end

function http_responce.okResponce3(errcode,errmsg,data)
    local tbResponce = {};
    tbResponce["ret"] = true;
    tbResponce["errcode"] = errcode;
    tbResponce["errmsg"] = errmsg;
    tbResponce["data"] = data;
    local json = require "cjson"
    return json.encode(tbResponce);
end

function http_responce.failResponce(errcode,errmsg,data)
    local tbResponce = {};
    tbResponce["ret"] = false;
    tbResponce["errcode"] = errcode;
    tbResponce["errmsg"] = errmsg;
    tbResponce["data"] = data;

    local json = require "cjson"
    return json.encode(tbResponce);
end

return http_responce