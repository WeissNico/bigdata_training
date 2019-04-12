# This script redeploys sherlock to the IBM cluster.
# Author: Johannes Mueller <j.mueller@reply.de>

# the name of the resource group
$RESOURCE_GROUP = "sherlock-prod"
# the cluster name
$CLUSTER_NAME = "test"
# the container name
$KIBANA_CR = "de.icr.io/bluereplyde/kibana"

# login to ibmcloud this asks for user and password
do {
    Write-Host "Trying to login to IBMcloud..." -ForegroundColor yellow
    ibmcloud login
} while($LASTEXITCODE -ne 0) 

# target the resourcegroup
ibmcloud target -g $RESOURCE_GROUP

# get clusterconfig
Write-Host "Retrieve Cluster Config..." -ForegroundColor yellow
$output = (ibmcloud ks cluster-config $CLUSTER_NAME) | Out-String
if ($output -match '[^=]+\.yml') {
    $clusterpath = $matches[0]
}
$env:KUBECONFIG = $clusterpath
Write-Host "DONE" -ForegroundColor green

# login to container registry
Write-Host "Login to Container Registry..." -ForegroundColor yellow
ibmcloud cr login
Write-Host "DONE" -ForegroundColor green

# delete container due to space constraints
Write-Host "Delete kibana container from container registry..." -ForegroundColor yellow
ibmcloud cr image-rm $KIBANA_CR
Write-Host "DONE" -ForegroundColor green

# build container
Write-Host "Build new kibana container..." -ForegroundColor yellow
docker build -t kibana ${PSScriptRoot}\kibana_deploy
Write-Host "DONE" -ForegroundColor green

# Push container
Write-Host "Tag and push kibana container..." -ForegroundColor yellow
docker tag kibana ${KIBANA_CR}:latest
docker push $KIBANA_CR
Write-Host "DONE" -ForegroundColor green

# delete kubernetes deployment
Write-Host "Delete kubernetes deployment..." -ForegroundColor yellow
kubectl delete -f ${PSScriptRoot}\kibana-deploy.yml
Write-Host "DONE" -ForegroundColor green

# create kubernetes deployment
Write-Host "Delete kubernetes deployment..." -ForegroundColor yellow
kubectl create -f ${PSScriptRoot}\kibana-deploy.yml
Write-Host "DONE" -ForegroundColor green