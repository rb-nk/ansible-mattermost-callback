# -*- coding: utf-8 -*-

# Ronny Bolzendahl <rbolzendahl@netzkraefte.de>
# Inspired by slack-callback module:
# (C) 2014-2015, Matt Martz <matt@sivel.net>
# (C) 2017 Ansible Project
# 
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    author: Ronny Bolzendahl
    name: mattermost
    type: notification
    requirements:
      - whitelist in configuration
      - prettytable (python library)
    short_description: Sends play events to a Mattermaost channel
    description:
        - This is an ansible callback plugin that sends status updates to a Mattermost channel during playbook execution.
    options:
      api_key:
        required: True
        description: Mattermost API-KEY
        env:
          - name: MATTERMOST_API_KEY
        ini:
          - section: callback_mattermost
            key: api_key
      mattermost_url:
        required: True
        description: Mattermost Webhook URL
        env:
          - name: MATTERMOST_URL
        ini:
          - section: callback_mattermost
            key: mattermost_url
      channel:
        default: "#ansible"
        description: Mattermost room to post in.
        env:
          - name: MATTERMOST_CHANNEL
        ini:
          - section: callback_mattermost
            key: channel
      username:
        description: Username to post as.
        env:
          - name: MATTERMOST_USERNAME
        default: ansible
        ini:
          - section: callback_mattermost
            key: username
      validate_certs:
        description: validate the SSL certificate of the Mattermost server. (For HTTPS URLs)
        env:
          - name: MATTERMOST_VALIDATE_CERTS
        ini:
          - section: callback_mattermost
            key: validate_certs
        default: True
        type: bool
      timer_format:
        desciption: format of the string shown to user at play end
        ini:
          - section: callback_mattermost
            key: timer_format
        env:
          - name: MATTERMOST_TIMER_FORMAT
        default: "Playbook run took %s days, %s hours, %s minutes, %s seconds"
      show_update_result:
        description: show hostwise installed updates
        env:
          - name: MATTERMOST_SHOW_UPDATE_RESULT
        ini:
          - section: callback_mattermost
            key: show_update_result
        default: False
        type: bool
      update_task_name:
        description: name of task, that returns update infos
        env:
          - name: MATTERMOST_UPDATE_TASK_NAME
        ini:
          - section: callback_mattermost
            key: update_task_name
      use_bot:
        descrition: use bot instead of webhook. NOTE Need channel_id to be set if bot should be used
        env:
          - name: MATTERMOST_USE_BOT
        ini:
          - section: callback_mattermost
            key: use_bot
        default: false
        type: bool
      channel_id:
        description: id of the channel to post in
        env:
          - name: MATTERMOST_CHANNEL_ID
        ini:
         - section: callback_mattermost
           key: channel_id
        
'''

import json
import os
import uuid

from ansible import context
from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.urls import open_url
from ansible.plugins.callback import CallbackBase

try:
    import prettytable
    HAS_PRETTYTABLE = True
except ImportError:
    HAS_PRETTYTABLE = False

from datetime import datetime

class CallbackModule(CallbackBase):
    """This is an ansible callback plugin that sends status
    updates to a Mattermost channel during playbook execution.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'community.general.mattermost'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self, display=None):

        super(CallbackModule, self).__init__(display=display)

        if not HAS_PRETTYTABLE:
            self.disabled = True
            self._display.warning('The `prettytable` python module is not '
                                  'installed. Disabling the Mattermost callback '
                                  'plugin.')

        self.playbook_name = None
        self.updateRes = {}

        #start timer when plugin is loaded
        self.start_time = datetime.now()

        # This is a 6 character identifier provided with each message
        # This makes it easier to correlate messages when there are more
        # than 1 simultaneous playbooks running
        self.guid = uuid.uuid4().hex[:6]

    def set_options(self, task_keys=None, var_options=None, direct=None):

        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)
        self.use_bot = self.get_option('use_bot')
        self.url = self.get_option('mattermost_url')
        self.api_key = self.get_option('api_key')
        if self.use_bot:
            self.webhook_url = "{0}/api/v4/posts".format(self.url)
        else:
            self.webhook_url = "{0}/hooks/{1}".format(self.url, self.api_key)
        #self.webhook_url = self.get_option('webhook_url')
        self.channel = self.get_option('channel')
        self.channel_id = self.get_option('channel_id')
        self.username = self.get_option('username')
        self.show_invocation = (self._display.verbosity > 1)
        self.validate_certs = self.get_option('validate_certs')
        self.icon_url = 'https://cdn2.hubspot.net/hub/330046/file-449187601-png/ansible_badge.png'

        if self.webhook_url is None:
            self.disabled = True
            self._display.warning('Mattermost Webhook URL was not provided. The '
                                  'Mattermost Webhook URL can be provided using '
                                  'the `MATTERMOST_URL` environment '
                                  'variable.')

    def send_msg(self, attachments, text = ''):
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
        }

        payload = {
            'channel': self.channel,
            'channel_id': self.channel_id,
            'username': self.username,
            'attachments': attachments,
            'text': text,
            'icon_url': self.icon_url,
        }

        if self.use_bot:
            headers = {
              'Content-type': 'application/json',
              'Authorization': 'Bearer ' + self.api_key,
            }
            payload = {
                'channel_id': self.channel_id,
                'props': {
                    'attachments': attachments,
                }
            }

        data = json.dumps(payload)
        self._display.debug(data)
        self._display.debug(self.webhook_url)
        try:
            response = open_url(self.webhook_url, data=data, validate_certs=self.validate_certs,
                                headers=headers)
            return response.read()
        except Exception as e:
            self._display.warning('Could not submit message to Mattermost: %s' %
                                  to_text(e) + data + ' :: ' + self.webhook_url)

    def _days_hours_minutes_seconds(self, runtime):
        #helper for time format
        minutes = (runtime.seconds // 60) % 60
        r_seconds = runtime.seconds - (minutes * 60)
        return runtime.days, runtime.seconds // 3600, minutes, r_seconds

    def v2_playbook_on_start(self, playbook):
        self.playbook_name = os.path.basename(playbook._file_name)
        text = ''

        title = [
            '*Playbook initiated* (_%s_)' % self.guid
        ]

        invocation_items = []
        if context.CLIARGS and self.show_invocation:
            tags = context.CLIARGS['tags']
            skip_tags = context.CLIARGS['skip_tags']
            extra_vars = context.CLIARGS['extra_vars']
            subset = context.CLIARGS['subset']
            inventory = [os.path.abspath(i) for i in context.CLIARGS['inventory']]

            invocation_items.append('Inventory:  %s' % ', '.join(inventory))
            if tags and tags != ['all']:
                invocation_items.append('Tags:       %s' % ', '.join(tags))
            if skip_tags:
                invocation_items.append('Skip Tags:  %s' % ', '.join(skip_tags))
            if subset:
                invocation_items.append('Limit:      %s' % subset)
            if extra_vars:
                invocation_items.append('Extra Vars: %s' %
                                        ' '.join(extra_vars))

            title.append('by *%s*' % context.CLIARGS['remote_user'])

        title.append('\n\n*%s*' % self.playbook_name)
        msg_items = [' '.join(title)]
        if invocation_items:
            msg_items.append('```\n%s\n```' % '\n'.join(invocation_items))

        msg = '\n'.join(msg_items)

        attachments = [{
            'fallback': msg,
            'fields': [
                {
                    'value': msg
                }
            ],
            'color': 'warning',
            'mrkdwn_in': ['text', 'fallback', 'fields'],
        }]

        self.send_msg(attachments=attachments, text=text)

    def v2_playbook_on_play_start(self, play):
        """Display Play start messages"""
        
        name = play.name or 'Play name not specified (%s)' % play._uuid
        msg = '*Starting play* (_%s_)\n\n*%s*' % (self.guid, name)
        attachments = [
            {
                'fallback': msg,
                'text': msg,
                'color': 'warning',
                'mrkdwn_in': ['text', 'fallback', 'fields'],
            }
        ]
        self.send_msg(attachments=attachments)

    def v2_runner_on_ok(self, result):
        """gather info about result output, save them for stats use"""
        host = result._host.get_name()
        
        text = host + ' :: ' + self._dump_results(result._result) + ' || ' + result._task.get_name()

        #for key in list(result.keys()):
        #    text += key + ' || ' + self._dump_results(result[key],indent=4) + "\n"
        

        attachments = [
            {
                'fallback': text,
                'text': text,
                'color': 'good',
                'mrkdwn_in': ['text', 'fallback', 'fields'],
            }
        ]

        if self.get_option('show_update_result') == True and result._task.get_name() == self.get_option('update_task_name'):
            self.updateRes[host] = result._result


        #self.updateRes[host] = result._result

        # for k in result._result.updates:
        #   self.updateRes[host].append({
        #       'update': result._result.updates[k].title + ' - ' + 'installed: ' + result._result.updates[k].installed
        #   })
         
        # self.send_msg(attachments=attachments)
        

    def v2_playbook_on_stats(self, stats):
        """Display info about playbook statistics"""

        text = ''

        end_time = datetime.now()
        runtime = end_time - self.start_time

        text = self._plugin_options['timer_format'] % (self._days_hours_minutes_seconds(runtime))

        hosts = sorted(stats.processed.keys())

        t = prettytable.PrettyTable(['Host', 'Ok', 'Changed', 'Unreachable',
                                     'Failures', 'Rescued', 'Ignored'])

        resT = prettytable.PrettyTable(['Host', 'Failed updates', 'Installed Updates', 'Reboot Required', "Updates"])

        failures = False
        unreachable = False

        for h in hosts:
            s = stats.summarize(h)

            if s['failures'] > 0:
                failures = True
            if s['unreachable'] > 0:
                unreachable = True

            t.add_row([h] + [s[k] for k in ['ok', 'changed', 'unreachable',
                                            'failures', 'rescued', 'ignored']])
            if h in self.updateRes.keys():
                resText = json.dumps(self.updateRes[h])
                updates = ''
                for u in self.updateRes[h]['updates']:
                    updates = self.updateRes[h]['updates'][u].title + ' :: installed: ' + self.updateRes[h]['updates'][u].installed + "\n"

                resT.add_row([h] + [self.updateRes[h][v] for v in ['failed_update_count', 'installed_update_count', 'reboot_required']] + [updates])

        attachments = []
        msg_items = [
            '*Playbook Complete* (_%s_)' % self.guid
        ]
        if failures or unreachable:
            color = 'danger'
            msg_items.append('\n*Failed!*')
        else:
            color = 'good'
            msg_items.append('\n*Success!*')

        msg_items.append('```\n%s\n```' % resT)
        msg_items.append('```\n%s\n```' % t)

        msg = '\n'.join(msg_items)

        attachments.append({
            'fallback': msg,
            'fields': [
                {
                    'value': msg
                }
            ],
            'color': color,
            'mrkdwn_in': ['text', 'fallback', 'fields']
        })

        self.send_msg(attachments=attachments, text=text)
