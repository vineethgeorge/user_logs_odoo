# -*- coding: utf-8 -*-
##############################################################################
#
#
#     This file is part of user_logs, an Odoo module.
#     This Modules is upgraded with new features like ip address browser and other features,
#     Improved performance
#     Copyright (c) 2015 GeosoftTechnologies (<http://GeosoftTechnologies>)
#     inactive_session_timeout is free software: you can redistribute it
#     and/or modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     inactive_session_timeout is distributed in the hope that it will
#     be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with inactive_session_timeout.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
import datetime
from openerp.http import request
import logging

from openerp.http import root
from openerp.http import request

from os import utime
from os.path import getmtime
from time import time
from openerp import http

import httpagentparser
from itertools import chain

_logger = logging.getLogger('======User Logs===')
USER_PRIVATE_FIELDS = ['password']
concat = chain.from_iterable


class res_users(osv.osv):
    _inherit='res.users'
    _description = "User Log Details"
    _columns = {
        'user_log_ids': fields.one2many('res.users.log','user_id','User Logs'),
    }

    def authenticate(self, db, login, password, user_agent_env):#added by vineeth
        
        uid = super(res_users, self).authenticate(db, login, password, user_agent_env)
        try:
            ip_address = request.httprequest.environ['HTTP_X_FORWARDED_FOR']
        except:
            ip_address = request.httprequest.environ['REMOTE_ADDR']
        agent = request.httprequest.environ.get('HTTP_USER_AGENT')
        agent_details = httpagentparser.detect(agent)
        user_os = agent_details.get('os', "Unknown")
        if user_os:
            os_name=user_os.get('name',"Unknown")
        else:
            os_name="Unknown"
        browser=agent_details.get('browser', "Unknown")
        if browser:
            browser_name=browser.get('name', "Unknown")+' Version:'+browser.get('version', "Unknown")
        else:
            browser_name="Unknown"
        sign_in = datetime.datetime.now()
        if uid:
            cr = self.pool.cursor()
            session_id=False
            try:
                session_id = request.session_id
                self.pool.get('res.users.log').create(cr, uid,{'user_id':uid,
                                                               'sign_in':sign_in,
                                                               'session_id':session_id,
                                                               'ip_address':ip_address,
                                                               'browser':browser_name,
                                                               'os':os_name,
                                                               'status':"Successfully logged in"})
                cr.commit()
                cr.close()
            except Exception,e:
                cr.close()
                _logger.info("Exception======%s",e)
                
        else:
            cr = self.pool.cursor()
            cr.execute("""SELECT id FROM res_users where login=%s;""",(login,))
            try:
                uid=cr.fetchone()[0]
                sign_in = datetime.datetime.now()
                self.pool.get('res.users.log').create(cr, uid,{'user_id':uid,
                                                               'sign_in':sign_in,
                                                               'ip_address':ip_address,
                                                               'browser':browser_name,
                                                               'os':os_name,
                                                               'status':"Failed to login"})
                cr.commit()
                cr.close()
                uid=False
            except Exception,e:
                cr.close()
                _logger.info("Exception======%s",e)
        return uid

    def _check_session_validity(self, db, uid, passwd):
         
        if not request:
            return
        session = request.session
        session_store = root.session_store
        param_obj = self.pool['ir.config_parameter']
        delay, urls = param_obj.get_session_parameters(db)
        deadline = time() - delay
        path = session_store.get_session_filename(session.sid)
        try:
            if getmtime(path) < deadline:
                if session.db and session.uid:
                    cr = self.pool.cursor()
                    log_pool = self.pool.get('res.users.log')
                    sign_out = datetime.datetime.now()
                    session_id = request.session_id
                    log_id = log_pool.search(cr, uid, [('session_id','=',session_id)])
                    log_pool.write(cr,uid,log_id,{'sign_out':sign_out,
                                                  'status':"session expired"})
                    cr.commit()
                    cr.close()
                    session.logout(keep_db=True)
            elif http.request.httprequest.path not in urls:
                # the session is not expired, update the last modification
                # and access time.
                utime(path, None)
        except OSError:
            pass
        return


    def check(self, db, uid, passwd):
        res=super(res_users, self).check(db, uid, passwd)
        self._check_session_validity(db, uid, passwd)
        try:
            req = request.httprequest
            base_url = req.base_url
            if base_url.split('/')[-1] == 'logout':
                cr = self.pool.cursor()
                log_pool = self.pool.get('res.users.log')
                sign_out = datetime.datetime.now()
                session_id = request.session_id
                log_id = log_pool.search(cr, uid, [('session_id','=',session_id)])
                log_pool.write(cr,uid,log_id,{'sign_out':sign_out,
                                              'status':"Successfully logged out"})
                cr.commit()
                cr.close()
        except Exception,e:
            _logger.info("=======%s",e)
        return res

class res_users_log(osv.osv):
    _name='res.users.log'
    _order = 'sign_in desc'
    _columns={
              'user_id': fields.many2one('res.users','User'),
              'sign_in':fields.datetime('Login Time'),
              'sign_out':fields.datetime('Logout Time'),
              'session_id':fields.char('Session ID'),
              'ip_address':fields.char('Ip address'),#added by vineeth
              'browser':fields.char('Browser'),#added by vineeth
              'os':fields.char('Operating system'),#added by vineeth
              'status':fields.char('Status')#added by vineeth
              }
