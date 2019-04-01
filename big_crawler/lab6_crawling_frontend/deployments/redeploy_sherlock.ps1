# This script redeploys sherlock to the IBM cluster.
# Author: Johannes Mueller <j.mueller@reply.de>

# the name of the resource group
$RESOURCE_GROUP = "sherlock-prod"
# the cluster name
$CLUSTER_NAME = "mycluster"
# the container name
$SHERLOCK_CR = "de.icr.io/bluereplyde/sherlock"

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
Write-Host "Delete sherlock container..." -ForegroundColor yellow
ibmcloud cr image-rm $SHERLOCK_CR
Write-Host "DONE" -ForegroundColor green

# build container
Write-Host "Build sherlock container..." -ForegroundColor yellow
docker build -t sherlock ${PSScriptRoot}\..
Write-Host "DONE" -ForegroundColor green

# Push container
Write-Host "Tag and push sherlock container..." -ForegroundColor yellow
docker tag sherlock ${SHERLOCK_CR}:latest
docker push $SHERLOCK_CR
Write-Host "DONE" -ForegroundColor green

# delete kubernetes deployment
Write-Host "Delete kubernetes deployment..." -ForegroundColor yellow
kubectl delete -f ${PSScriptRoot}\sherlock-deploy.yml
Write-Host "DONE" -ForegroundColor green

# create kubernetes deployment
Write-Host "Delete kubernetes deployment..." -ForegroundColor yellow
kubectl create -f ${PSScriptRoot}\sherlock-deploy.yml
Write-Host "DONE" -ForegroundColor green