--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/8/2
-- Time: 下午12:46
-- To change this template use File | Settings | File Templates.
--


local responce = require("utils/http_responce")
local request_method = ngx.var.request_method


if "GET" == request_method then
    local inArgs = ngx.req.get_uri_args()
    local md5Encoder = require ("md5")

    local inip = inArgs["ip"]
    local wrtlist = require('checks.selfiplist')

    if "table" ~= type(wrtlist) then
        ngx.say(responce.failResponce(-1,"ip block",""));
    else
        for i = 1, #wrtlist do
            local myipmd5 = md5Encoder.sumhexa(wrtlist[i]);

            if string.upper(inip) == string.upper(myipmd5) then
                ngx.say(responce.okResponce("ip check pass"))
                ngx.exit(200);
            end
        end
        ngx.say(responce.failResponce(-1,"ip block",""));
    end
elseif "POST" == request_method then
    ngx.say(responce.failResponce(-1,"no post",""))
end

