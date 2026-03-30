# Install docker

Make sure APT is using the proxy properly.

```bash
sudo tee /etc/apt/apt.conf.d/99proxy >/dev/null <<'EOF'
Acquire::http::Proxy "http://127.0.0.1:1087";
Acquire::https::Proxy "http://127.0.0.1:1087";
EOF
```

Add the docker repo properly.

```bash
# remove old docker if needed (optional but safer)
sudo apt-get remove docker docker-engine docker.io containerd runc

# install dependencies
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# add Docker GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# add repo
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# install docker + buildx
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```