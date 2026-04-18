# Stateless Failover PoC

Use this reference for deployment, switching, and verification of the Karmada failover demo.

## Verified Assets

All proven PoC artifacts already exist in the repo:

- app: `/root/karmada/samples/failover-demo/app`
- manifests: `/root/karmada/samples/failover-demo/manifests`
- helper scripts: `/root/karmada/samples/failover-demo/scripts`

The important design choices are:

- Karmada manages the workload and service placement.
- `OverridePolicy` injects `cluster 1` into `member1` and `cluster 2` into `member2`.
- A host-side HAProxy instance exposes one stable entrypoint on `:8088`.
- `member1` is the primary backend.
- `member2` is the hot standby backend.
- The page proves continuity with successful probes, a heartbeat timeline, and recent switch events.

## Deploy The Demo

From the demo directory:

```bash
export PATH=/usr/local/go/bin:/root/go/bin:/root/.local/bin:$PATH
cd /root/karmada/samples/failover-demo
./scripts/build-and-load.sh
./scripts/deploy.sh
./scripts/start-proxy.sh
```

Expected outcome:

- the image `karmada/failover-demo:v1` is built once and loaded into `member1` and `member2`
- `failover-demo` rolls out on both member clusters
- `http://127.0.0.1:8088/` becomes reachable
- `http://127.0.0.1:8088/status` initially reports `cluster 1`

## Check Direct And Proxied Endpoints

Use both direct member endpoints and the stable host endpoint:

```bash
member1_ip="$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' member1-control-plane)"
member2_ip="$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' member2-control-plane)"

curl "http://${member1_ip}:30088/status"
curl "http://${member2_ip}:30088/status"
curl "http://127.0.0.1:8088/status"
```

Expected semantics:

- direct `member1` response says `cluster 1`
- direct `member2` response says `cluster 2`
- proxied response starts on `cluster 1`

## Trigger Failover To Cluster 2

```bash
cd /root/karmada/samples/failover-demo
./scripts/fail-member1.sh
```

This stops `member1-control-plane`. The host proxy health check should fail over to `member2` within a few seconds.

Verify:

```bash
curl "http://127.0.0.1:8088/status"
```

Expected outcome:

- proxied endpoint changes from `cluster 1` to `cluster 2`
- the browser page stays on the same URL
- the successful probe count keeps increasing if the cutover stayed clean

## Converge Karmada Placement To Cluster 2

Use this only after traffic is already on `cluster 2`:

```bash
cd /root/karmada/samples/failover-demo
./scripts/promote-member2.sh
```

This patches:

- the deployment replica count to `1`
- the deployment `PropagationPolicy` to only target `member2`
- the service `PropagationPolicy` to only target `member2`

## Recover Cluster 1 And Fail Back

Bring `member1` back:

```bash
docker start member1-control-plane
```

If the demo resources were converged to `member2`, redeploy them before failback:

```bash
cd /root/karmada/samples/failover-demo
./scripts/build-and-load.sh
./scripts/deploy.sh
```

Then restore the proxy so `member1` is primary again:

```bash
./scripts/start-proxy.sh
curl "http://127.0.0.1:8088/status"
```

Expected outcome:

- direct `member1` endpoint is healthy again
- proxied endpoint returns `cluster 1`
- the browser page logs a switch event from `cluster 2` to `cluster 1`

## Core Validation Commands

Karmada view:

```bash
kubectl --kubeconfig=/root/.kube/karmada.config --context=karmada-apiserver get deployment,propagationpolicy,overridepolicy,resourcebinding -n default | grep failover-demo
```

Member view:

```bash
kubectl --kubeconfig=/root/.kube/members.config --context=member1 get deploy,svc,pod -n default
kubectl --kubeconfig=/root/.kube/members.config --context=member2 get deploy,svc,pod -n default
```

Convenience status script:

```bash
cd /root/karmada/samples/failover-demo
./scripts/status.sh
```

## What This PoC Proves

- Karmada can distribute one app definition to multiple member clusters.
- `OverridePolicy` can make each member present a different identity.
- A stable user entrypoint can fail over between clusters without changing the browser URL.
- Stateless traffic can be cut over cleanly when the standby cluster is already warm.

## What This PoC Does Not Prove

- application state replication
- database failover
- uninterrupted long-lived TCP sessions
- Karmada alone performing zero-gap traffic switching without an external entrypoint
