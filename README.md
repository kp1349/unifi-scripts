# unifi-scripts
This repo houses python scripts that can be used to configure a Unifi cloud gateway ultra

## setup
```sh
pip install -r requirements.txt

mv port_forward.yaml.template port_forward.yaml
mv static_ips.yaml.template static_ips.yaml
mv .evn.template .env
# update all files
```
To get your username and password, go to your unifi network settings and search for 'Admins & Users' — this account needs to be local only, no MFA

## run
```sh
python static_ips.py

python port_forward.py
```
