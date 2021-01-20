#!/bin/env python

import os, re, array, math
import time

## safe batch mode                                 
import sys
args = sys.argv[:]
sys.argv = ['-b']
import ROOT
sys.argv = args
ROOT.gROOT.SetBatch(True)
ROOT.PyConfig.IgnoreCommandLineOptions = True

#sys.path.append(os.getcwd() + "/plotUtils/")
from utility import *

ROOT.gROOT.SetBatch(True)

# hardcoded stuff for now, will make it option later
file_Eflow = {"prompt2018" : "hotspotStudies_EE_eflow_2018Prompt_4d_v2.root",
              "UL2018"     : "hotspotStudies_EE_eflow_2018UL_4d.root"
}
tree_Eflow = "ee"
#-----------
file_Zee   = {"prompt2018" : "hotspotStudies_ZeeIC_2018Prompt.root",
              "UL2018"     : "hotspotStudies_ZeeIC_2018UL.root"
}
tree_Zee   = "ZeeICtree"
#------------
file_hotChannels = "hot_channels_list_v2.root" # from Alejandro
tree_hotChannels = "tHotspots"
# IC and laser correction (LC) values from Alejandro's trees
# use IC and LC from last era in case 2018 is used (LC should be larger with time, but it is fine when searching for fancy crystals)
varLC_hotChannels = {"prompt2018" : "lcEOY18D",
                     "UL2018"     : "lcUL18D"
}
varIC_hotChannels = {"prompt2018" : "icEOY18D",
                     "UL2018"     : "icUL18D"}
#------------
campaigns = ["prompt2018", "UL2018"]
#--------


def initializeHisto(h, val=0.0,err=0.0):
    if h.GetDimension()==1:
        for i in range(0,1+h.GetNbinsX()):
            h.SetBinContent(i,val)
            h.SetBinError(i,err)
    elif h.GetDimension()==2:
        for i in range(0,1+h.GetNbinsX()):
            for j in range(0,1+h.GetNbinsY()):
                h.SetBinContent(i,j,val)
                h.SetBinError(i,j,err)        

def copyHisto(hin, hout):
    if hin.GetDimension() != hout.GetDimension():
        print "Error in copyHisto(): the two histograms have different dimensions"
        quit()
    if hin.GetDimension()==1:
        for i in range(0,1+hin.GetNbinsX()):
            hout.SetBinContent(i,hin.GetBinContent(i))
            hout.SetBinError(i,hin.GetBinError(i))
    elif hin.GetDimension()==2:
        for i in range(0,1+hin.GetNbinsX()):
            for j in range(0,1+hin.GetNbinsY()):
                hout.SetBinContent(i,j,hin.GetBinContent(i,j))
                hout.SetBinError(i,j,hin.GetBinError(i,j))        


def getHistoFromFile(fname,hname):
    tf = ROOT.TFile.Open(fname)        
    if not tf or tf.IsZombie():
        print "ERROR! Unable to open file %s" % fname
        quit()
    h = tf.Get(hname)
    if not h:
        print "ERROR! Unable to get histogram %s in %s" % (hname,fname)
        quit()
    h.SetDirectory(0)
    tf.Close()
    return h


def getTreeFromFile(fname,treename):
    tf = ROOT.TFile.Open(fname)        
    if not tf or tf.IsZombie():
        print "ERROR! Unable to open file %s" % fname
        quit()
    tree = tf.Get(treename)
    if not tree:
        print "ERROR! Unable to get tree %s in %s" % (treename,fname)
        quit()
    #tree.SetDirectory(0)
    #tf.Close()
    return tree


def treeToHisto(tree, h, expr, cuts="1"):    
    if ROOT.gROOT.FindObject("dummy") != None: 
        ROOT.gROOT.FindObject("dummy").Delete()
    hdummy = None
    if h.GetDimension()==1:
        hdummy = ROOT.TH1D("dummy","",
                           h.GetNbinsX(),
                           h.GetXaxis().GetBinLowEdge(1),
                           h.GetXaxis().GetBinLowEdge(1+h.GetNbinsX())
                       )
        
    elif h.GetDimension()==2:
        hdummy = ROOT.TH2D("dummy","",
                           h.GetNbinsX(),
                           h.GetXaxis().GetBinLowEdge(1),
                           h.GetXaxis().GetBinLowEdge(1+h.GetNbinsX()),
                           h.GetNbinsY(),
                           h.GetYaxis().GetBinLowEdge(1),
                           h.GetYaxis().GetBinLowEdge(1+h.GetNbinsY())
                       )

    else:
        print "Error in treeToHisto(): dimensions > 2 not supported"
        quit()
        
    tree.Draw("%s>>dummy" % (expr), cuts, "goff")
    #hdummy = ROOT.gDirectory.Get("dummy");
    hdummy = ROOT.gROOT.FindObject("dummy")
    hdummy.SetDirectory(0)
    print "hdummy.GetDimension() = %s    hdummy.Integral() = %.1f" % (hdummy.GetDimension(), hdummy.Integral())
    copyHisto(hdummy,h)
    return 0


if __name__ == "__main__":
            
    from optparse import OptionParser
    parser = OptionParser(usage='%prog [options] file1 hist1 file2 hist2')
    parser.add_option('-o','--outdir',      dest='outdir',      default='', type='string', help='output directory to save things')
    parser.add_option('-i','--indir',      dest='indir',      default='root://eosproject.cern.ch//eos/project/c/cms-ecal-calibration/www/Run2_hotspot_studies/', type='string', help='Input directory to read things')
    parser.add_option('-c','--campaign',      dest='campaign',      default='UL2018', type='string', help='Campaign to select trees: UL2018, prompt2018, etc...')
    (options, args) = parser.parse_args()

    outname = ""
    if options.outdir:
        outname = options.outdir
        addStringToEnd(outname,"/",notAddIfEndswithMatch=True)
        createPlotDirAndCopyPhp(outname)
    else:
        print "Error: you should specify an output folder using option -o <name>. Exit"
        quit()

    if options.campaign not in campaigns:
        print "Error: campaign must be in [%s]" % ",".join(str(x) for x in campaigns)
        quit()
    campaign = options.campaign

    year = str(re.findall(r'\d+',campaign)[0])

    # # get histograms for converting EE crystals into eta-ring number (from 0 to 38)
    # file_xyzToEtaRing = "/afs/cern.ch/user/m/mciprian/public/ECALproTools/EE_xyzToEtaRing/eerings_modified.root"
    # h_xyzToEtaRing = {}
    # for izside in range(2):
    #     h_xyzToEtaRing[izside] = getHistoFromFile(file_xyzToEtaRing,"hEEm" if izside == 0 else "hEEp")
    ##
    ## can use Alejandro's tree

    h2_Eflow_iz = {}
    h2_Zee_iz = {}
    h2_hotChannels_status_iz = {}  # status = 0 for good channels, > 0 for hotspots (actual value depends on
    h2_hotChannels_iring_iz = {} # from 0 to 38
    h2_hotChannels_worst_iz = {}  # identifies worst hotspot, for which it is 1, all other crystals are 0
    h2_hotChannels_LC_iz = {}
    h2_hotChannels_IC_iz = {}
    h2_hotChannels_LCtimesIC_iz = {}
    for izside in range(2):
        h2_Eflow_iz[izside] = ROOT.TH2D("h2_Eflow_%s" % ("EEp" if izside else "EEm"),"Eflow %s" % ("EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
        #initializeHisto(h2_Eflow_iz[izside],-100)
        h2_Zee_iz[izside] =   ROOT.TH2D("h2_Zee_%s"   % ("EEp" if izside else "EEm"),"Zee %s" % ("EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
        #initializeHisto(h2_Zee_iz[izside],-100)
        h2_hotChannels_status_iz[izside] = ROOT.TH2D("h2_hotChannels_status_%s" % ("EEp" if izside else "EEm"),"hotspot status %s" % ("EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
        h2_hotChannels_iring_iz[izside] = ROOT.TH2D("h2_hotChannels_iring_%s" % ("EEp" if izside else "EEm"),"hotspot etaring %s" % ("EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
        h2_hotChannels_worst_iz[izside] =  ROOT.TH2D("h2_hotChannels_worst_%s"  % ("EEp" if izside else "EEm"),"hotspot isBigOffender %s" % ("EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
        for ctype in ["UL","prompt"]:
            cname = ctype+year
            h2_hotChannels_LC_iz[(izside,cname)] =   ROOT.TH2D("h2_hotChannels_LC_%s_%s"   % (cname, "EEp" if izside else "EEm"),"%s %s" % (cname, "EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
            h2_hotChannels_IC_iz[(izside,cname)] =   ROOT.TH2D("h2_hotChannels_IC_%s_%s"   % (cname, "EEp" if izside else "EEm"),"%s %s" % (cname, "EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)
            h2_hotChannels_LCtimesIC_iz[(izside,cname)] =   ROOT.TH2D("h2_hotChannels_LCtimesIC_%s_%s"   % (cname, "EEp" if izside else "EEm"),"%s %s" % (cname, "EE+" if izside else "EE-"),100,0.5,100.5,100,0.5,100.5)

    #t_Eflow = getTreeFromFile(options.indir+file_Eflow[campaign],tree_Eflow)

    # Eflow tree
    filename = options.indir+file_Eflow[campaign]
    tf_Eflow = ROOT.TFile.Open(filename,'read')        
    if not tf_Eflow or tf_Eflow.IsZombie():
        print "ERROR! Unable to open file %s" % filename
        quit()
    treename = tree_Eflow
    t_Eflow = tf_Eflow.Get(treename)
    if not t_Eflow:
        print "ERROR! Unable to get tree %s in %s" % (treename,filename)
        quit()

    # Zee tree
    filename = options.indir+file_Zee[campaign]
    tf_Zee = ROOT.TFile.Open(filename,'read')        
    if not tf_Zee or tf_Zee.IsZombie():
        print "ERROR! Unable to open file %s" % filename
        quit()
    treename = tree_Zee
    t_Zee = tf_Zee.Get(treename)
    if not t_Zee:
        print "ERROR! Unable to get tree %s in %s" % (treename,filename)
        quit()

    # hotChannels tree
    filename = options.indir+file_hotChannels
    tf_hotChannels = ROOT.TFile.Open(filename,'read')        
    if not tf_hotChannels or tf_hotChannels.IsZombie():
        print "ERROR! Unable to open file %s" % filename
        quit()
    treename = tree_hotChannels
    t_hotChannels = tf_hotChannels.Get(treename)
    if not t_hotChannels:
        print "ERROR! Unable to get tree %s in %s" % (treename,filename)
        quit()


    # print "-"*30
    # print t_Eflow.GetEntries()
    # print "\n".join(str(x.GetName()) for x in t_Eflow.GetListOfLeaves())
    # print "-"*30

    #treeToHisto(t_Eflow,h2_Eflow,"ix:iy",cuts="slope")
    adjustSettings_CMS_lumi()
    canvas2D = ROOT.TCanvas("canvas2D","",1200,1000)

    #####################################
    # start loops to retrieve information
    # might use AddFriends to exploit a single loop, but the hashId/hashedId variable is named differently in some trees for now (will be fixed later)
    # in addition, some variables like the slope should be named differently between Zee and Eflow, so I can't use friends right now
    for event in t_hotChannels:
        izside = 0 if event.iz < 0 else 1
        h2_hotChannels_status_iz[izside].Fill(event.ix,event.iy,event.istatus)
        h2_hotChannels_iring_iz[izside].Fill(event.ix,event.iy,event.iring)
        h2_hotChannels_worst_iz[izside].Fill(event.ix,event.iy,event.iworst)
#************************************************************************
#*    Row   *        ix *        iy *        iz *   istatus *    iworst *
#************************************************************************
#*     2901 *        42 *        41 *        -1 *         1 *         1 *
#*     4596 *        52 *        62 *        -1 *         2 *         1 *
#*    11025 *        62 *        51 *         1 *         1 *         1 *
#*    11183 *        64 *        53 *         1 *         1 *         1 *
#*    11659 *        42 *        59 *         1 *         1 *         1 *
#*    12193 *        43 *        65 *         1 *         2 *         1 *
#************************************************************************
        for ctype in ["UL", "prompt"]:
            cname = ctype + year
            varLC = getattr(event,varLC_hotChannels[cname])
            varIC = getattr(event,varIC_hotChannels[cname])
            if math.isnan(abs(varLC)): continue # protection, but expect no strange values here
            if math.isnan(abs(varIC)): continue # protection, but expect no strange values here
            h2_hotChannels_LC_iz[(izside,cname)].Fill(event.ix,event.iy,varLC)
            h2_hotChannels_IC_iz[(izside,cname)].Fill(event.ix,event.iy,varIC)
            h2_hotChannels_LCtimesIC_iz[(izside,cname)].Fill(event.ix,event.iy,varLC*varIC)

    logVars = ["boh"] # dummy
    #logVars = ["slope"]
    varToPlot = "slope"

    gr_Eflow_IC = {} # key will be (ix, iy, iz), and created only for large IC*LC
    gr_Zee_IC = {} # key will be (ix, iy, iz), and created only for large IC*LC
    # the following might become input options
    minICtimesLC = 50
    #minDiffICtimesLC_promptUL = 10
    #minRelDiffICtimesLC_promptUL = 0.5
    minRatioLCtimeIC_promptUL = 3
    # list of xtals to plot (a random selection such that they are on a segment at constant iX)
    xtalsToPlot = [(50,10,1), (50,20,1), (50,30,1), (50,32,1), (50,33,1), (50,35,1), (50,37,1)]

    val_LC = {}
    val_IC = {}

    info_xtal = {}

    for event in t_Eflow:
        izside = 0 if event.iz < 0 else 1
        varVal = getattr(event,varToPlot)
        if math.isnan(abs(varVal)): continue # some values are -999        
        if varToPlot in logVars:
            varVal_tmp = math.log10(abs(varVal))
            varVal = varVal_tmp if varVal > 0 else -1.0 * varVal_tmp
        for ctype in ["UL", "prompt"]:
            cname = ctype + year
            val_LC[ctype] = h2_hotChannels_LC_iz[(izside,cname)].GetBinContent(event.ix,event.iy) 
            val_IC[ctype] = h2_hotChannels_IC_iz[(izside,cname)].GetBinContent(event.ix,event.iy) 
        
        ICtimesLC_prompt = val_LC["prompt"] * val_IC["prompt"]
        ICtimesLC_UL = val_LC["UL"] * val_IC["UL"]
        ICtimesLC = ICtimesLC_prompt if "prompt" in campaign else ICtimesLC_UL
        ICtimesLC_absDiff_promptUL = abs(ICtimesLC_prompt-ICtimesLC_UL)
        ICtimesLC_relDiff_promptUL = ICtimesLC_absDiff_promptUL/ICtimesLC_prompt
        ICtimesLC_ratio_promptUL = ICtimesLC_prompt/ICtimesLC_UL
        #if ICtimesLC > minICtimesLC or (ICtimesLC_absDiff_promptUL > minDiffICtimesLC_promptUL and ICtimesLC_relDiff_promptUL > minRelDiffICtimesLC_promptUL):
        isHotSpot = True if h2_hotChannels_status_iz[izside].GetBinContent(event.ix,event.iy) > 0 else False
        isHotSpotWorstOffender = True if (isHotSpot and h2_hotChannels_worst_iz[izside].GetBinContent(event.ix,event.iy) == 1) else False
        if ICtimesLC_prompt > minICtimesLC or ICtimesLC_ratio_promptUL > minRatioLCtimeIC_promptUL or (event.ix,event.iy,event.iz) in xtalsToPlot or isHotSpot:
            Niovs = int(event.n_iovs)
            key = (event.ix,event.iy,event.iz)
            gr_Eflow_IC[key] = ROOT.TGraphAsymmErrors(Niovs)            
            gr_Eflow_IC[key].SetName("ICvsIOV_Eflow_ix_%d_iy_%d_%s" % (event.ix,event.iy,("EEp" if izside else "EEm")))
            gr_Eflow_IC[key].SetTitle("%s ix=%d iy=%d" % (("EE+" if izside else "EE-"),event.ix,event.iy))
            info_xtal[key] = "%s  ix=%d  iy=%d  iRing=%d/39  %s;prompt: LC=%.2f, IC=%.3f;UL:       LC=%.2f, IC=%.3f " % (("EE+" if izside else "EE-"),event.ix,event.iy,1+h2_hotChannels_iring_iz[izside].GetBinContent(event.ix,event.iy),"isWorstHotspot" if isHotSpotWorstOffender else "isHotspot" if isHotSpot else "", val_LC["prompt"],val_IC["prompt"],val_LC["UL"],val_IC["UL"])
            for n in range(Niovs):
                gr_Eflow_IC[key].SetPoint(n,event.avg_time[n],event.ic_ratio_eflow[n])            

        h2_Eflow_iz[izside].Fill(event.ix,event.iy,varVal)
        

    for event in t_Zee:
        izside = 0 if event.iz < 0 else 1
        varVal = getattr(event,varToPlot)
        if math.isnan(abs(varVal)): continue
        if (varVal-(-999)) < 0.001: continue  # values for |eta|<2.5 are -999, keep histogram empty there
        if varToPlot in logVars:
            varVal_tmp = math.log10(abs(varVal))
            varVal = varVal_tmp if varVal > 0 else -1.0 * varVal_tmp
        for ctype in ["UL", "prompt"]:
            cname = ctype + year
            val_LC[ctype] = h2_hotChannels_LC_iz[(izside,cname)].GetBinContent(event.ix,event.iy) 
            val_IC[ctype] = h2_hotChannels_IC_iz[(izside,cname)].GetBinContent(event.ix,event.iy) 
        
        ICtimesLC_prompt = val_LC["prompt"] * val_IC["prompt"]
        ICtimesLC_UL = val_LC["UL"] * val_IC["UL"]
        ICtimesLC = ICtimesLC_prompt if "prompt" in campaign else ICtimesLC_UL
        ICtimesLC_absDiff_promptUL = abs(ICtimesLC_prompt-ICtimesLC_UL)
        ICtimesLC_relDiff_promptUL = ICtimesLC_absDiff_promptUL/ICtimesLC_prompt
        ICtimesLC_ratio_promptUL = ICtimesLC_prompt/ICtimesLC_UL
        #if ICtimesLC > minICtimesLC or (ICtimesLC_absDiff_promptUL > minDiffICtimesLC_promptUL and ICtimesLC_relDiff_promptUL > minRelDiffICtimesLC_promptUL):
        isHotSpot = True if h2_hotChannels_status_iz[izside].GetBinContent(event.ix,event.iy) > 0 else False
        isHotSpotWorstOffender = True if (isHotSpot and h2_hotChannels_worst_iz[izside].GetBinContent(event.ix,event.iy) == 1) else False
        if ICtimesLC_prompt > minICtimesLC or ICtimesLC_ratio_promptUL > minRatioLCtimeIC_promptUL or (event.ix,event.iy,event.iz) in xtalsToPlot or isHotSpot:
            Niovs = int(event.n_iovs)
            key = (event.ix,event.iy,event.iz)
            gr_Zee_IC[key] = ROOT.TGraphAsymmErrors(Niovs)            
            gr_Zee_IC[key].SetName("ICvsIOV_Zee_ix_%d_iy_%d_%s" % (event.ix,event.iy,("EEp" if izside else "EEm")))
            gr_Zee_IC[key].SetTitle("%s ix=%d iy=%d" % (("EE+" if izside else "EE-"),event.ix,event.iy))
            for n in range(Niovs):
                gr_Zee_IC[key].SetPoint(n,event.time[n],event.ZeeIC[n])            
        h2_Zee_iz[izside].Fill(event.ix,event.iy,varVal)

    #print "gr_Eflow_IC.keys() = %s" % gr_Eflow_IC.keys()
    #print "gr_Zee_IC.keys() = %s" % gr_Zee_IC.keys()

    for key in gr_Eflow_IC.keys():
        graphs = [gr_Eflow_IC[key]]
        legEntries = ["Eflow"]
        if key in gr_Zee_IC:
            graphs.append(gr_Zee_IC[key])
            legEntries.append("Zee")
        title = info_xtal[key]
        title += "::0.18,0.86,0.08,0.04"  # to pass as 'moreTextLatex' argument to drawNGraph
        # if "prompt" in campaign:
        #     title += "::0.18,0.86,0.08,0.04"  # to pass as 'moreTextLatex' argument to drawNGraph
        # else:
        #     title += "::0.38,0.36,0.08,0.04"
        yTitle = "intercalibration constant (%s)::%s" % (campaign, "0,1.5" if "prompt" in campaign else "0.5,2.0")
        #yTitle = "intercalibration constant (%s)::0,1.5" % (campaign)
        drawNGraph(graphs,legEntries,
                   "timestamp",yTitle,
                   gr_Eflow_IC[key].GetName().replace("_Eflow",""),
                   outname, rightMargin=0.08, legendCoords="0.15,0.45,0.2,%s" % (str(0.20+0.08*len(graphs))),
                   passCanvas=canvas2D, moreTextLatex=title)

    for izside in range(2):

        # draw LC and IC
        for ctype in ["UL", "prompt"]:
            cname = ctype + year
            maxVal = min(40,h2_hotChannels_LC_iz[(izside,cname)].GetBinContent(h2_hotChannels_LC_iz[(izside,cname)].GetMaximumBin()))
            drawCorrelationPlot(h2_hotChannels_LC_iz[(izside,cname)],"ix","iy","LC::0,%s" % maxVal,
                                h2_hotChannels_LC_iz[(izside,cname)].GetName(),
                                "ForceTitle",outname,0,0,False,False,False,
                                1,palette=ROOT.kTemperatureMap,passCanvas=canvas2D,drawOption="COLZ0",
                                printMinMaxZ=True,zTitleOffset=1.1)
            maxVal = min(5.5,h2_hotChannels_IC_iz[(izside,cname)].GetBinContent(h2_hotChannels_IC_iz[(izside,cname)].GetMaximumBin()))
            drawCorrelationPlot(h2_hotChannels_IC_iz[(izside,cname)],"ix","iy","IC::0,%s" % maxVal,
                                h2_hotChannels_IC_iz[(izside,cname)].GetName(),
                                "ForceTitle",outname,0,0,False,False,False,
                                1,palette=ROOT.kTemperatureMap,passCanvas=canvas2D,drawOption="COLZ0",
                                printMinMaxZ=True,zTitleOffset=1.1)
            maxVal = min(40,h2_hotChannels_LCtimesIC_iz[(izside,cname)].GetBinContent(h2_hotChannels_LCtimesIC_iz[(izside,cname)].GetMaximumBin()))
            drawCorrelationPlot(h2_hotChannels_LCtimesIC_iz[(izside,cname)],"ix","iy","LC*IC::0,%s" % maxVal,
                                h2_hotChannels_LCtimesIC_iz[(izside,cname)].GetName(),
                                "ForceTitle",outname,0,0,False,False,False,
                                1,palette=ROOT.kTemperatureMap,passCanvas=canvas2D,drawOption="COLZ0",
                                printMinMaxZ=True,zTitleOffset=1.1)
        
        LCtimesIC_ratioPromptUL_iz = h2_hotChannels_LCtimesIC_iz[(izside,"prompt"+year)].Clone(h2_hotChannels_LCtimesIC_iz[(izside,"prompt"+year)].GetName().replace("prompt","ratioPromptUL"))
        LCtimesIC_ratioPromptUL_iz.SetTitle(LCtimesIC_ratioPromptUL_iz.GetTitle().replace("prompt","prompt/UL "))
        LCtimesIC_ratioPromptUL_iz.Divide(h2_hotChannels_LCtimesIC_iz[(izside,"UL"+year)])
        maxVal = min(5,LCtimesIC_ratioPromptUL_iz.GetBinContent(LCtimesIC_ratioPromptUL_iz.GetMaximumBin()))
        drawCorrelationPlot(LCtimesIC_ratioPromptUL_iz,"ix","iy",
                            "(LC*IC)_{prompt} / (LC*IC)_{UL}::0.5,%s" % maxVal,
                            LCtimesIC_ratioPromptUL_iz.GetName(),
                            "ForceTitle",outname,0,0,False,False,False,
                            1,palette=ROOT.kTemperatureMap,passCanvas=canvas2D,drawOption="COLZ0",
                            printMinMaxZ=True,zTitleOffset=1.1)

            
        minv,maxv = getMinMaxHisto(h2_Eflow_iz[izside],excludeEmpty=True,sumError=False,excludeMin=-0.5, excludeMax=0.5)
        #minv = h2_Eflow_iz[izside].GetBinContent(h2_Eflow_iz[izside].GetMinimumBin())
        #maxv = h2_Eflow_iz[izside].GetBinContent(h2_Eflow_iz[izside].GetMaximumBin())
        #print "min = %f    max = %f" % (minv,maxv)
        absmax1 = max(abs(minv),abs(maxv))

        minv,maxv = getMinMaxHisto(h2_Zee_iz[izside],excludeEmpty=True,sumError=False,excludeMin=-0.5, excludeMax=0.5)
        #minv = h2_Zee_iz[izside].GetBinContent(h2_Zee_iz[izside].GetMinimumBin())
        #maxv = h2_Zee_iz[izside].GetBinContent(h2_Zee_iz[izside].GetMaximumBin())
        #print "min = %f    max = %f" % (minv,maxv)
        absmax2 = max(abs(minv),abs(maxv))

        absmax = max(absmax1, absmax2)
        #zAxisTitle = "%s::%f,%f" % (varToPlot,-absmax1,absmax1)
        #zAxisTitle = "%s" % (varToPlot)
        zAxisTitle = "%s::-2e-8,2e-8" % (varToPlot) # to be adapted based on values
        # draw
        drawCorrelationPlot(h2_Eflow_iz[izside],"ix","iy",zAxisTitle,
                            h2_Eflow_iz[izside].GetName(),"ForceTitle",outname,0,0,False,False,False,
                            1,palette=-1,passCanvas=canvas2D,drawOption="COLZ0",zTitleOffset=1.1)
        #zAxisTitle = "%s::%f,%f" % (varToPlot,-absmax2,absmax2)
        #zAxisTitle = "%s::-2e-8,2e-8" % (varToPlot)
        drawCorrelationPlot(h2_Zee_iz[izside],"ix","iy",zAxisTitle,
                            h2_Zee_iz[izside].GetName(),"ForceTitle",outname,0,0,False,False,False,
                            1,palette=-1,passCanvas=canvas2D,drawOption="COLZ0",zTitleOffset=1.1)
        # get ratio
        h2_EflowOverZee = h2_Eflow_iz[izside].Clone(h2_Eflow_iz[izside].GetName().replace("Eflow","EflowOverZee"))
        h2_EflowOverZee.SetTitle("ratio %s: (Eflow - Zee) / Zee" % ("EE+" if izside else "EE-"))
        h2_EflowOverZee.Add(h2_Zee_iz[izside],-1)
        h2_EflowOverZee.Divide(h2_Zee_iz[izside])
        zAxisTitleRatio = "%s::-1,1" % (varToPlot)
        drawCorrelationPlot(h2_EflowOverZee,"ix","iy", "ratio " + zAxisTitleRatio,
                            h2_EflowOverZee.GetName(),"ForceTitle",outname,0,0,False,False,False,
                            1,palette=-1,passCanvas=canvas2D,drawOption="COLZ0",zTitleOffset=1.1)
