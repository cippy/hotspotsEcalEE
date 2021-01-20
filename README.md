# Get the code
```
cmsrel CMSSW_10_6_18
cd CMSSW_10_6_18/src/
cmsenv
git remote add cippy git@github.com:cippy/hotspotsEcalEE.git
YOUR_GITHUB_REPOSITORY=$(git config user.github) # or set it manually if this doesn't work for you
git clone git@github.com:cippy/hotspotsEcalEE.git hotspotsEcalEE
cd hotspotsEcalEE
git remote add origin git@github.com:$YOUR_GITHUB_REPOSITORY/hotspotsEcalEE.git
```
Now you can develop as you like, and commit to your own repository
You can also open pull requests to other repositories if the project is used by many people

# Usage
```
python makeHotSpotStudy.py -o /path/to/web/page/
```
where /path/to/web/page/ is the location where you want to store plots.
Check for more options inside the script
