# Karmada Bootstrap And Teardown

Use this reference when installing, validating, or removing the local Karmada environment.

## Fastest Verified Bring-Up

From the repo root:

```bash
export PATH=/usr/local/go/bin:/root/go/bin:/root/.local/bin:$PATH
cd /root/karmada
hack/local-up-karmada.sh
```

This is the repo-supported local bootstrap. It:

- prepares the development base
- creates the `karmada-host` kind cluster
- deploys the Karmada control plane
- joins `member1` and `member2`
- also creates `member3` in pull mode
- writes kubeconfigs to `/root/.kube/karmada.config` and `/root/.kube/members.config`

For this PoC, `member3` is not used. Keep it unless the user explicitly asks for a custom minimal topology.

## Contexts To Use

Karmada control plane:

```bash
export KUBECONFIG=/root/.kube/karmada.config
kubectl config use-context karmada-apiserver
```

Member clusters:

```bash
export KUBECONFIG=/root/.kube/members.config
kubectl config use-context member1
kubectl config use-context member2
```

## Minimum Validation

Run these checks after bootstrap:

```bash
kubectl --kubeconfig=/root/.kube/karmada.config --context=karmada-apiserver get clusters
kubectl --kubeconfig=/root/.kube/members.config --context=member1 get nodes
kubectl --kubeconfig=/root/.kube/members.config --context=member2 get nodes
```

Healthy output should show:

- `member1` and `member2` in `Ready=True`
- a ready control-plane node in each member cluster

## When Bootstrap Partially Fails

Check:

```bash
kind get clusters
docker ps -a | rg 'karmada-host|member1|member2|member3'
```

Common repairs:

- missing `kind` in `PATH`: export the known good `PATH` and rerun
- kubeconfig missing after a previous cleanup: redeploy with `hack/local-up-karmada.sh`
- one member cluster unhealthy: inspect the matching `*-control-plane` container logs before recreating everything

## Teardown

Preferred cleanup:

```bash
export PATH=/usr/local/go/bin:/root/go/bin:/root/.local/bin:$PATH
cd /root/karmada
hack/local-down-karmada.sh
```

If the environment is partially broken and the script cannot run cleanly, delete explicitly:

```bash
kind delete cluster --name karmada-host
kind delete cluster --name member1
kind delete cluster --name member2
kind delete cluster --name member3
rm -f /root/.kube/karmada.config /root/.kube/members.config
```

Then verify:

```bash
kind get clusters
docker ps -a --format '{{.Names}}' | rg '^(karmada-host|member1|member2|member3)(-|$)'
```
