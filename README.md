# Mattermost Callback

Plugin for reporting of ansible-playbook results to a Mattermost-Channel.

The plugin was written since the scheduler of the gitlab only produced mails and results to failed or successful pipes in CI / CD, but lacks info on what succeeded or went wrong or even wich tasks where running. So this is where this callback steps up and posts the play infos to a mattermost channel.
Since there is a community-callback plugin for slack, doing what I expected from it, I reworked it to fit for mattermost.
Improvements welcome

## Installation
1. install python libraries 
   ```sh
   $ pip install prettytable
   $ pip install requests --upgrade
   ```

2. Download plugin and create a folder callback_plugins where your playbooks reside, which should use the callback
   
   ```sh
   $ cd /path/to/playbooks
   $ mkdir callback_plugins
   $ curl -O https://raw.githubusercontent.com/rb-nk/ansible-mattermost-callback/main/mattermost.py
   ```

3. Add config to your ansible.cfg

   ```sh
   callback_whitelist = mattermost

   [callback_mattermost]
   api_key = ENTER_TOKEN
   mattermost_url = https://matter.my.domain
   username = someuser
   channel = somechanel
   validate_certs = true
   use_bot = true
   channel_id = ENTER_CHAN_ID
   show_update_result = True
   update_task_name = 'Install updates'
   ```

## Roadmap
- Features to come: more detailed output on tasks
- more options on output

## Authors and acknowledgment
Thanks to the original authors of the slack callback - used most their code and modified it to work with mattermost, which is little to none effort

## License
GPL v3

## Project status
functional release, exploring options for more features
