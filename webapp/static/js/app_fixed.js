/**
 * Exam Grader Application JavaScript
 * Common functionality and utilities
 */

// Application namespace
var ExamGrader = ExamGrader || {};

// Application namespace
ExamGrader = {

  // Configuration
  config: {
    maxFileSize: 100 * 1024 * 1024, // 100MB (increased from 16MB)
    allowedFileTypes: [
      ".pdf",
      ".docx",
      ".doc",
      ".jpg",
      ".jpeg",
      ".png",
      ".tiff",
      ".bmp",
      ".gif",
    ],
    apiEndpoints: {
      processMapping: "/api/process-mapping",
      processGrading: "/api/process-grading",
    },
  },

  // Notification Manager
  notificationManager: {
    // Get user's notification level preference
    getNotificationLevel: function () {
      // Try to get from localStorage first
      const storedLevel = localStorage.getItem('notification_level');
      if (storedLevel) {
        return storedLevel;
      }

      // Try to get from DOM if available
      const levelSelect = document.getElementById('notification_level');
      if (levelSelect && levelSelect.value) {
        return levelSelect.value;
      }

      // Default to 'all' if not found
      return 'all';
    },

    // Check if notification should be shown based on type and user preference
    shouldShowNotific
});nit();
  }xamGrader.i E{
   r.init) xamGradeined' && Er !== 'undefExamGradetypeof 
  if (() {function ntLoaded', Contener('DOMListeentaddEv
document. loadedis DOM enze whtiali// Ini
  }
}

y = 'none';yle.displadal.st   mo(modal) {
 l');
  if ailsModayId('det.getElementBocument = dst modall() {
  conModatailstion closeDe
func();
}
sults.exportReamGrader.api
  Exalled');lts cxportResu'ensole.log( coults() {
 exportResnction 
}

fur');
  });rrosage}`, 'e{error.mesls: $load detaito fy(`Failed nager.notiMaotificationader.n    ExamGr', error);
s:detailn  submissiorror loading.error('Ensole
    co=> {h(error 
  .catc
  })  }
  tails');ssion de load submitod or || 'FailerrError(data.ew new      thro{
   } else al);
  d(modpendChil.apbodyent.   docum
   
      `;      </div>  </div>
  
        div>    </        >
 </button      
            Close           ()">
move.rexed')ficlosest('.his.ick="tm" onclm:text-sw-auto snone sm:ne-cus:outli foay-50r:bg-grve00 hoxt-gray-7m tediuase font-met-bbg-white texx-4 py-2 -sm pdoway-300 shaer border-grd-md bord roundeenterjustify-cx flell inline-fu"w-" class=uttonn type="b      <butto
        everse">w-rm:flex-rolex s-6 sm:f-3 sm:px0 px-4 pyg-gray-5"bass=iv cl    <d     div>
          <//div>
              <    2)}</pre>
 null, n, missiota.subngify(da{JSON.stried">$oundp-4 r-50 rayap bg-gpace-pre-wrtesy-700 whi-sm text-graass="text<pre cl           
     ">s="mt-2v clas   <di        s</h3>
   n Detailubmissiomb-4">S-900 m text-grayfont-mediuing-6 adg leass="text-l    <h3 cl         b-4">
 6 sm:p pb-4 sm:p- pt-5x-4white p="bg- <div class           ">
llsm:w-fu2xl -w- sm:maxiddlesm:align-msm:my-8 sition-all sform tran tranw-xlhadoden sw-hidt overfloleflg text-nded-rouite bg-whn-bottom lock aligine-bs="inlas    <div cl
      ()"></div>removet.parentElemenment.learentE"this.pck=" onclin-opacitynsitio75 traopacity- bg- bg-gray-500ed inset-0lass="fixv c<di     ">
      sm:p-0m:blocknter st-cetex px-4 pb-20 n pt-4reeter min-h-scustify-cen-end jex items="flclass   <div   `
   HTML = ner   modal.in  auto';
 erflow-y-z-50 ov-0 'fixed insetame = .classN     modal('div');
 eElementt.creatocumen= d modal onst
      cetailsmission dubith smodal w  // Show ) {
    a.successif (dat
    n(data => { .theET'
  })
 d: 'G metho
   }`, {nIdubmissios/${setailn-dbmissio/api/suequest(`piRder.utils.aGra
  Examdetailsmission wing subr viefoementation 
  // Impl }
return;
 or');
     ID', 'errsubmissionvalid Inotify('nManager.nificatiomGrader.not) {
    ExasionId if (!submisd);

 ionIn:', submisssubmissioled for wDetails calole.log('vieconsionId) {
  ls(submissiewDetai
function vilitympatibrd cor backwaions fonctal fu// Glob }
};

');
 tializedrader iniog('ExamGle.lconso    system
 otificationitialize n
    // In;
    toRefresh()nitAuf.ithis.csrement
    agann mF tokeize CSR  // Initial  ction () {
 init: funtion
 cae appliialize th
  // Init,
   }
  }
 );
      }l.remove(       moda
 ) {  if (modaldal');
    -mo('progresstElementByIdment.geal = docu  const mod    ) {
on (odal: functigressMidePro */
    h
    modals e progres
     * Hid

    /** }
    },
     tage)}%`;nd(percen`${Math.rou|| ssage ment = xtContecentage.teressPer   prog{
     ge) Percentaif (progress         }

  age))}%`;
 , percent(00, Math.maxMath.min(10`${ = dth.wiBar.style progress       {
ressBar)  if (prog

     age');-percentd('progresstElementByI.gement docue =entagressPercog pr      constar');
'progress-blementById(cument.getEdosBar = progresonst    c  age) {
 age, mession (percentunct fsModal:rogrespdateP   */
    ual
  ogress modpr * Update   
  

    /**l);
    },(modaChildody.append.b   document       `;

 </div>
  
       /div>  <     
      </div>         div>
</           iv>
   /d           </div>
                <     >
  ">0%</pter2 text-cen0 mt--gray-50ext-sm textass="t clentage"s-percid="progres   <p           >
              </div           "></div>
  dth: 0% style="wiion-300"-all duratitionll transfuunded-.5 roue-600 h-2"bg-blar" class=ress-brog="p<div id                 
     h-2.5">ounded-full gray-200 rfull bg-class="w-       <div             
 }</p>${message-4">ay-500 mbext-grtext-sm tp class="     <        >
       "ss="mt-2<div cla               h3>
   title}</>${900 mb-4"t-gray-edium texnt-mding-6 folg leatext-="lass  <h3 c              full">
  ft w--le-0 sm:texter sm:mt3 text-cent class="mt-iv    <d        art">
    ems-stsm:it"sm:flex <div class=            :pb-4">
  :p-6 sm5 pb-4 smx-4 pt-e pitlass="bg-wh      <div cl">
      ful-lg sm:w-x-wmae sm:ign-middl:alsm:my-8 sml ransition-alransform t shadow-xl trflow-hiddenxt-left oveunded-lg tewhite ron-bottom bg-e-block aligs="inlin   <div clasan>
       /sp#8203;<">&creenle sm:h-sn-midd:alig-block smlinedden sm:inclass="hi <span >
         "></divcityansition-opa trg-opacity-7500 b-gray-5nset-0 bg"fixed iass=cldiv 
          <k sm:p-0">m:blocter sext-cenpb-20 tt-4 px-4 screen pmin-h-enter stify-cms-end juex ite"flass= <div cl    = `
    MLinnerHTmodal.     y-auto';
 verflow-set-0 z-50 o= 'fixed insName   modal.clasdal';
    ogress-mo'pr modal.id = 
     ('div');eateElementnt.crumedal = doc   const most.') {
    your reque we processait whilese wge = 'Plea...', messaocessing 'Prtitle =ction ( funsModal:res showProg    */
 
   ress modalw prog Sho
     * /**ui: {
   ents
   compon/ UI},

  /    }
    }

    , 'error');r.message}`led: ${erro`Export faiotify(nager.nnMaotificatioer.namGrad    Ex);
    roror:', erport errerror('Ex    console. {
    h (error)} catc');
      ', 'successfully!cessrted suc expoesults.notify('RnagertionMaca.notifierad      ExamGr);

  eChild(abody.remov   document.    (url);
 eObjectURLL.revok window.UR      ck();
     a.cli
    dChild(a);.body.appendocument
        lsx';esults.x= 'exam_road  a.downll;
        = ura.href
        = 'none';display   a.style.
      nt('a');emeteElument.creanst a = doc co;
       tURL(blob).createObjecow.URLt url = wind       conslob();
 t response.b= awai blob   const
      
     }  failed');
 uest 'Export reqw Error(row ne        thse.ok) {
  spon (!re        if

      }); },
         Token(),
  r.csrf.getamGradeken': Ex'X-CSRFTo         ,
   on'on/jsatilic 'app':Typeontent-   'C     : {
        headers     ST',
 : 'POthod     me
     lts', {export-resupi/h('/a= await fetce onst respons   c{
         try ) {
  nction ( async futResults:
    expor
     */ results    * Export*
 },

    /*
      }r;
    ow erro      thr
  );, erroress:"ting progrgetrror ror("Ee.er consol       rror) {
} catch (e
      rn data;tu re
       ;      )
       }
     "GET",d:      metho  
               {`,
Id}rogressess/${p `/api/progr      equest(
   iRs.apGrader.utilwait Exama = aatonst d    c
     {try   
   d) {ogressIunction (pr async fProgress: */
    get
    statusss progreGet   *    /**
   ,

 
    } };
     urn falseet
        rrror");ge}`, "eerror.messa ${g failed:y(`Gradinotifnager.ncationMa.notifier    ExamGrad   rror) {
  catch (e     } }
       
 ");ing failed"Grador || rr.ew Error(data throw ne      lse {
   } e
        rn true;  retu      ;
   )      ess"
   ucc"s    
        ssfully!",cced sung complete    "Gradi    fy(
    nager.notionMaicatider.notifExamGra        {
  a.success) (dat  if 

              );}

          OST",hod: "P      met          {
 ,
     ssGradingts.procepiEndpoin.config.amGraderExa      quest(
    Reils.apixamGrader.utwait Eta = a   const datry {
     
      n () {ctiofun async rading:essGproc*/
    ding
     ss gra* Proce*
     

    /*}
    },lse;
       return fa       r");
ge}`, "errosa{error.mesd: $ileping faapify(`Mer.notanagtificationMrader.no     ExamG{
   tch (error)   } ca          }
 );
 ed"pping fail| "Madata.error |ew Error(row nth          {
       } else
  true;   return  );
             ccess"
   su     "      lly!",
 cessfued suc completmapping   "Answer       notify(
   onManager.otificatier.nad    ExamGr  
     {ccess)ta.su(da if ;

       }
        )  ,
        od: "POST"       meth{
            ping,
   sMapnts.procesig.apiEndpoirader.confxamG        Equest(
  utils.apiRemGrader.it Exawanst data = a     co try {
   () {
     ion unct async fcessMapping: pro     */
   ng
 mappiswer* Process an/**
     {
    
  api: sionPI interact
  // A
  },

    }s;oreturn err}

      r     ");
 pportedpe not su ty("Fileors.push        errname)) {
leType(file.FisAlloweder.utils.if (!ExamGradpe
      i file ty    // Check   }

  ;
           )} limit`
         )ze
 maxFileSifig.mGrader.con      Exa    ize(
  matFileSs.forrader.utilExamG${e exceeds e siz       `Fils.push(
       error
     {leSize).maxFionfigr.cade ExamGr(file.size >
      if izefile s/ Check    /     }

rrors;
      return e);
      lected""No file serrors.push({
        ee)  (!fil
      if];
 = [ errors    const {
  on (file)nctie: fuilvalidateF    
     */
re uploadfo file beteValida* *
         /*

 }
    },    }
            }
 );
      ect(files[0]  onFileSel           {
eSelect) if (onFil      iles;
   ut.files = fnpeI   fil        0) {
.length > (files        iffiles;

 = dt. filesnst      co;
  Transfere.data =   const dt {
      leDrop(e)hand function     }

     e-50");
   "bg-blu0",-50ueblorder-.remove("bsListZone.clasop     dr   {
ht(e) ighlign unhctio

      fun    }");
  e-50 "bg-blu",-500"border-blued(.ade.classListpZonro{
        dighlight(e) n h     functio
 
      }
on();pagatiPro   e.stop
     fault();preventDe        e.ts(e) {
reventDefaulnction p
      fue);
Drop, fals handle","dropr(EventListenene.addopZo dres
      file dropped/ Handl

      /     }););
 false, unhighlightame, (eventNenerventList.addEZoneop dr
       me) => {h((eventNaorEac"].fopeave", "drragl      ["d
    });
false);
  ighlight, ntName, her(eveenddEventListne.a      dropZo=> {
  eventName) forEach((].agover"nter", "dr"drage  [   r it
 ove dragged item ishen op zone whlight dr/ Hig

      /);   }se);
   , falentDefaultsame, prev(eventNntListenervebody.addEument.       doc);
 lsefatDefaults, ventName, preer(evenstenventLi.addE  dropZone  => {
    eventName) ].forEach((""drope", ragleav"d, "dragover", r"dragente
      ["ors drag behavint default  // Preve

    t) return; !fileInpuZone ||   if (!drop
   leSelect) {nFieInput, oone, filction (dropZdDrop: funAnnitDrag   */
    i
  e uploaddrop for filze drag and nitiali   * I**
  ad: {
    /leUploity
  fiunctionalupload f// File 
    },

    }
ing();StrocaleTime date.toL() + " " +ateStringaleDate.toLoceturn d    rg);
  trinteSte(danew Dae = datonst     c;
  "Unknown"g) return  (!dateStrin
      ifng) {on (dateStrictie: funformatDat/
    ay
     *pl for disdate* Format   /**
     
  
 },
   
      };ter, wait);meout(latTieout = se        timtimeout);
eout(arTim  cle;
            }args);
      func(...t);
      meout(timeoulearTi    c=> {
      ) r = ( const late       s) {
n(...argunctio executedFunctionturn f     re;
 uteo timet l{
     unc, wait) (fction ununce: f/
    deboion
     *ce functeboun**
     * D    / },


   ";
      }00blue-8200 text-lue-order-b border b"bg-blue-50n tur    reult:
             defa
 ow-800";0 text-yellllow-20order-yeer b50 bordw-yellourn "bg-        reting":
  ase "warn;
        c"green-800200 text-r-green-borde50 border een-turn "bg-gr         re
 ess":"succ   case      d-800";
 text-re200der-red-or0 border b-red-5turn "bg         reor":
 se "err
        ca(type) {  switch pe) {
    tyon (ncti: fussageClassesgetMe*/
    es
     ssage typr meses foasS cl   * Get CS/**
  },

      ion);
  urat      }, d);
hidden"st.add("ea.classLiArmessage    {
      =>out(()ime  setT  ion
  fter duratAuto-hide a   // n");

   move("hiddereclassList.essageArea.      mage
e mess// Show th;

      sses(type)}`etMessageClathis.gext-sm ${d-md t rounde `mb-4 p-3me =assNaa.cl messageAre ones
     new add ses andclasng e existi // Remov   ge;

   = messaxtContentgeText.te  messa
    ling styntent andssage co  // Set me  

      }  ;
      returnon);
  type, duratie, st(messagowToa   this.sh   ");
  toast back to nd, fallingouents not felemrea Message arn("  console.wa    xt) {
  essageTeArea || !mmessage(!f  i
     -text");
sageId("mesElementBycument.geteText = donst messag co  rea");
   e-a("messaglementByIdnt.getE documegeArea =sat mes     cons {
 on = 5000)", durati "info type =n (message,unctiosage: fMessplay  di*/
  
     suto-dismisng and ad styliproveth imy message wi    * Displa
 

    /**r;
    },lastErro throw 
     tError);s:', lasretriel fter alt failed aAPI requeserror('  console.d
     faile retries here, allIf we get    //   }

        }
 }
              );
 olve, delay)esimeout(rtT see =>e(resolvisit new Prom awa           00);
- 1), 50, attempt h.pow(21000 * Matmin( = Math.delaynst       co
      ial backoffonent with expretryingre ait befo    // W      ries) {
  pt < maxRet (attem       if

      };
            break
       ) {ttempt > 1ror') && an er tokeRFdes('CScluessage.in(error.mif          rrors
  of ertain types for ce Don't retry     //    ror);

 failed:`, er${attempt} tempt att es requle.warn(`APIso      con    error;
=   lastError      
   r) {ch (erro} cat      ;
  tarn da      retu }

    
         Message);rrorew Error(e  throw n             }

        k;
       brea       
            }     nue;
       conti         ay));
    ve, delesoltTimeout(rve => sesolw Promise(re await ne                 ), 10000);
t - 1mpttepow(2, a * Math.00 Math.min(20 =nst delay   co           es) {
    Retrimaxtempt <       if (at      off
    backnential po with exr errorsy serve   // Retr       
      r.';aten lgai aease try Plerver error.'SMessage =   error           :
   se 500     ca   ak;
      re  b                 }
      
          continue;           ay));
    elolve, dmeout(reslve => setTimise(resot new Pro      awai            000);
 attempt, 15n(5000 *= Math.mit delay cons        
          es) {xRetri < maif (attempt             rors
   it err rate limng fore retryi befoait/ W     /          ';
 gain.ry ament and t mowait ats. Please requesy  mansage = 'ToorMes     erro    
        429:        case;
      eak br               
e.'; smaller file aooslease cho large. Pto= 'File age ssorMeerr                13:
    case 4
          k;    brea           ';
 the page.resh  reftoneed en. You may cess forbiddge = 'AcorMessa err            403:
    ase     c         break;
            0);
    00, 2          }in';
      '/auth/log.href = ioncat window.lo                  => {
meout(()      setTi       icated
   t authent login if noct to  // Redire   
           he page.';resh t. Please refredquiion reAuthenticatMessage = 'ror        er
        ase 401:         c  ;
   reak      b          }
              ';
  your input.eck se chest. PleaBad requrror || '.ee = dataMessag   error            lse {
         } e             }
                }, 3000);
              ;
     d()on.reloaati window.loc                 {
     ut(() =>setTimeo                   
  the pagereloadiled, so fay alf retr // I               {
        } else             
  equest the r/ Retry; /tinue    con               oken();
 efreshTr.csrf.r ExamGrade      await              ..');
n and retry. CSRF toke to refreshttemptingole.log('Acons          
          ) {pt === 1if (attem        
          once retry  andh CSRF tokenfres reto // Attempt                 ata);
 ed:', dtectror den er'CSRF tokele.error(onso       c     .';
      again and try  page refresh theleaseror. Pken erF toage = 'CSR  errorMess               ) {
 udes('csrf').inclerCase()Lowta.error.toror && daf (data.er    i   :
         ase 400           c{
   e.status) sponsre  switch (        

  atus}`;nse.st: ${respostatusror! TTP er|| `Hage a.messror || dat.eratasage = d errorMes      letes
      us codpecific statng with sor handlirrEnhanced e // 
           .ok) {esponsef (!r i  }

            
     ;se.text() }ont resp: awaigesaata = { mes      d   lse {
   } e         ;
 on().jsresponseta = await   da        ')) {
  ication/json'apples(udype.incl contentTpe &&tentTyif (con     ;
     t-type')tenet('coners.gponse.headType = restentonst con      c
    data;       let 
   typest content ene differ // Handl       });

   
         ectionSRF protokies for Cnclude con', // Igie-ori: 'samdentials     cre
       ined,ndef.body) : ufy(optionsSON.stringi? Jns.body dy: optio         bo},
              s,
 tions.header       ...op      ers,
 ultHeadfa..de  .             {
headers:           'POST',
  od ||.methnsptiood: oeth   m         st
ptions firl original oad al, // Spre  ...options     {
      url,etch(= await fesponse    const r
         }
       en;
  = csrfTokFToken']CSRaders['X- defaultHe          {
  en)if (csrfTok            };

  ",
      jsontion/ "applicae":tent-Typ"Con          rs = {
  ultHeadet defacons         }

          }
             or);
nErr', tokeRF token:fetch new CSto ('Failed onsole.error           crror) {
   h (tokenEtc       } ca}
                  equest');
 or API rtoken fSRF e Co retrievFailed tor('console.err               
 { else          });
     t'ques for API reF tokened new CSRievlly retrcessfulog('Suc  console.             {
  (csrfToken)       if ;
       eshToken().csrf.refrt ExamGraderawai = ken csrfTo          
   ry {       t  ism
   echanresh mg our reftoken usinnew CSRF  fetch a  Try to       //');
     refresh...g to tinOM. Attemp found in Dotken nRF towarn('CS    console. {
        Token)  if (!csrf
        ingfor debuggtatus ken sF to Log CSR     //  );

   getToken(.csrf.xamGraderen = ErfTok      let csurces
    multiple sole - try labif avaioken RF tdd CS        // A       try {
+) {
   ; attempt+etriesmpt <= maxRpt = 1; attettem (let afor      null;

 r =tErro     let lass = 3;
 maxRetriest   con {
    tions = {})url, opion ( async functiRequest: ap   */
   rity
  nd secuing adld error hanth enhance request wi * Make API*
    /*

       },ML;
 ton.innerHTlText || butnataset.origitton.da = buTMLtton.innerH    bu false;
  n.disabled =    butto;

  ton) return if (!but  n) {
   butto function (oading:eButtonL
    hid   */   button
ner onining sp Hide load
     *
    /**  },
   `;
  
         ingText}    ${load           /svg>
     <       h>
     "></pat3-2.647z8l 7.934 3 5.82.042 1.135c0 312H0962 0 014 .962 7.m2 5.291A773 0 12h4z 0 0 5.38V0C5.373a8 8 0 018-12or" d="M4 rentCol"curfill=5" city-7s="opa<path clas                   circle>
 h="4"></-widtstrokentColor" e="curre strok="10"cy="12" r" " cx="12ity-25ss="opaccircle cla        <          4 24">
  0 2="0 e" viewBox fill="non h-4 w-4"pin mr-2ate-snimass="a cl       <svg          `
rHTML =inne  button.    ed = true;
blsa.di      buttonML;
HT.innertonext = butinalTset.origbutton.data;

      turn re (!button)     ifg...") {
 ProcessingText = ", loadinonttnction (buading: futtonLoBu
    show*/  ton
   ner on buting spinow load    * Sh    /**
 

);
    }, }, duration     }
;
             }, 300)            }
     );
move(oast.re      t        Node) {
t.parent    if (toas        {
 (() =>eouttTim          se;
= "0"yle.opacity toast.st         t";
 3s ease-oucity 0.= "opasition style.tran     toast.     ode) {
rentNif (toast.pa{
        ut(() => Timeoset     ion
 er duratfto remove a // Aut

     toast);ppendChild(t.body.a   documen `;

            /div>
       <
           div>    </             
   </button>                   >
     svg       </            >
         evenodd"/ip-rule="14z" cl1 0 010-1.407a1 5.793 10 4.214L8.586 -1.414-1.4a1 1 0 014.293 4.29311.414l-4L10 .414 1.411-1a1 1 0 04.293 4.2934 10l11.411.414 1.414L0 11.293a1 1 .293-48.586l40L10 0 011.414  4.293a1 1 "M4.293" d=ddle="evenopath fill-ru    <                             20 20">
"0 0viewBox=" tColorill="curren4 w-4" fh-class="vg       <s                  ()">
    ment.removearentElelement.pent.parentEtElementhis.parck="lie-none" onccus:outlin        } folue-100"
-b hover:bg00ue-5-bl"text  :           0"
  -yellow-10500 hover:bgxt-yellow-"te          ? ing"
    = "warn : type ==     
      reen-100"ver:bg-g00 hoext-green-5       ? "t"
     successype === " t       :"
   d-100bg-re500 hover:xt-red- ? "te    "
     rorer= " ==5 ${typep-1.rounded-md line-flex in" class=""buttonype=n tutto   <b                   pl-3">
  l-auto "m=assiv cl    <d              iv>
         </d        >
     </pessage}    }">${m"
    ext-blue-800       : "t    w-800"
   lo? "text-yel           rning"
   wa"=== type     :       "
  -800ext-green       ? "tess"
     e === "succ     : typ     "
00text-red-8      ? "ror"
    = "er ${type ==nt-mediumext-sm fo<p class="t               
         3"> class="ml-     <div        
          </div>            
        }    /svg>'
 odd"/><rule="even1H9z" clip-1 1 0 00-1- 100-2v-3a 001 1h1a1 1 0 0v3a1 1 2a1 1 0 000012 0zM9 91 1 0  0 1-2 1 0 14a17- 0 0116 0zm-1-16 0 8 88 10a8 8 0 1 d="M1evenodd"fill-rule="th 20 20"><paox="0 0 wBlor" vierrentCocu" fill="xt-blue-500 w-5 te"h-5vg class=      : '<s     g>'
   svodd"/></rule="even" clip-1-1z 1 0 00-002 0V6a10 1 00-1 1v3a1  0  1m-1-8a1 012 0z-2 0 1 1 00 11M11 13a1 1 8-9.92z.53-2.98l57493-1.646-1.53 0-2.48H4.42c-1.2 2.92.98-1.741.334-.213 c.75 .92 0l5.58 986 3.4.722-1.36.36 2765-157 3.099c. d="M8.2venodd"ill-rule="e<path f 20">"0 0 20iewBox=Color" v"current= fill-500"t-yellow-5 w-5 texvg class="h<s     ? '   
      ng"rni=== "wa     : type   g>'
     ></svodd"/e="evenrul" clip-l4-4z14 01.41 0 004l2 2a1 14 1.411 0 00-1.4 9.293a1 7.7074L9 10.586 1.4114-1 0 00-1.41 707-9.293am3.8 0 000 16z0 100-16 8 0 18a8 8 dd" d="M1"evenoe=ill-rul"><path f 20 20="0 0viewBoxor" rrentColfill="cu-500" enw-5 text-gre"h-5 g class=<sv     ? '       ccess"
ype === "su     : t   svg>'
  d"/></odven="eclip-rule7 7.293z"  8.586 8.704-1.414L100 00-1.41-1.293a1 1 414 10l1.29314-1.414L11.01.43a1 1 0 0.293 1.29 11.414l11.414L101.414  0 10293a1 11..293 0l-1 1 1.414L8.586 00-1.4143a1 1 0.707 7.29M88 0 000 16z 8  100-16M10 18a8 8 0 d="venodd"l-rule="eath fil 20"><pox="0 0 20iewB vtColor"urrenll="c" fid-500 w-5 text-relass="h-5vg c? '<s       or"
   errtype === "      ${                ink-0">
  ex-shr"fls=v clas <di             ">
      s-centerflex itemass="  <div cl         L = `
     nerHTMtoast.in
         }`;
0"
     g-blue-5r-blue-500 brde "bo         :-50"
   -yellowbg500 r-yellow-de     ? "bor  "
     = "warning  : type ==      en-50"
  -500 bg-grerder-green "bo      ?s"
     "succespe ===       : ty
 bg-red-50"er-red-500  "bord      ?r"
  === "erro-up ${type te-slideima-4 andow-lg pd-lg shal-4 roundehite border-sm bg-w z-50 max-w- right-4xed top-4 `fiassName =st.cl
      toa");t("divenemteEl.creat = documentt toasons) {
      c= 5000tion dura,  = "info"essage, typen (mst: functiohowToa s   */
   fication
  oti toast n* Show**
      },

    /ext);
   includes(leTypes.wedFi.alloader.configrn ExamGr      retu
();aseerC).toLow".").pop(ename.split( + fil"."onst ext =   c
    se;) return fal (!filename if{
     filename)  (unctioneType: filwedFAllo   is*/
 owed
     s alltype ifile ck if     * Che   /**
 ,

 [i];
    }+ sizes " "(2)) + oFixed(k, i)).t.powathtes / Mt((byrseFloan pa     returog(k));
 ) / Math.l(bytes(Math.logath.floorst i = M     con"];
 ", "GB", "MB"KB",  = ["Bytesizest s
      cons024;onst k = 1     cs";
 urn "0 Byte === 0) ret(bytes
      if  {es) (bytze: functionSiatFile
    form*/mat
     dable forhuman reaze in t file si * Forma/**
    {
    : lsions
  utictun Utility f },

  //
 
    }imer();tInactivityTse    re  setup
itial    // In  ;

     })ue);
  trer, yTimetInactivitnt, resevestener(ventLit.addEcumen      dot => {
  ch(evenforEauchstart'].roll', 'toess', 'sce', 'keypr', 'mousemov['mousedown
      eventsy ser activit  // U };

        
 nactivityf is o minute/ 10); / 60 * 1000   }, 10 *e;
      = truserInactive       u{
   meout(() => er = setTityTimctivi  ina  }
           }
    );
       rroriled:', e refresh fatokened CSRF ctivity-baserror('Inasole.   con
         ror) {} catch (er        );
  freshToken(.re await this        
   try {
           = false;rInactive use
         ) {userInactive    if (mer);
    activityTieout(inim  clearT
      () => {er = async TimvityctitInaonst rese c

     vityTimer;tit inac
      lefalse;rInactive = se  let utivity
    ter inactive afmes acecor br useften aoke tshefre      // R);

 10000 * * 6Minutesnterval}, i
            }ror);
  ed:', erilesh faoken refrc CSRF tr('Periodile.erro conso
         rror) { (e  } catch      ken();
s.refreshTot thiwai      ary {
           t () => {
 asyncrval(   setInte  ally
 riodic peh token/ Refres      / = 30) {
esvalMinutinter (functionutoRefresh: tA    ini

     */icogoved lh imprh witfresn reRF toketomatic CStialize au
     * Ini

    /** },ll;
   turn nu
      re   }
value;
   nInput.turn altToke    reue) {
    put.valkenInltToput && atTokenIn      if (alen]');
tok[name=csrf-inputor('electrySdocument.queenInput = Tokltst aon    c
  e input nameivy alternat    // Tr   }

  ue;
   ut.valokenInp   return t
     ue) {nput.val tokenIt &&enInpu   if (tok
   ]');f_tokenname=csr('input[electorrySt.que= documennput const tokenI      s
rm input   // Try fo}

        ent');
 ('contttribute.getATagreturn meta     ) {
   content')te('ributtTag.getAmetametaTag &&       if ();
token]'f-name=csrmeta[elector('ent.querySg = docummetaTaonst      ctag first
 ta y me // Tr  on () {
   tiToken: func get  */
   k
   llbac faes withrcsoutiple en from mulCSRF tok
     * Get 
    /**},

    l;return nul
      Error);ed:', lastempts fail attn refreshll CSRF tokeor('Ansole.errco      


      }
        } }
         delay));ut(resolve,  setTimeoe(resolve =>misw Pro ne   await       0);
  500 1), empt -h.pow(2, attMat1000 * ath.min(st delay = M       con    ff
 ackotial bwith exponentrying ret before Wai         // 
   xRetries) {mpt < ma   if (atte    r);

   roed:`, er failtempt}atttempt ${ aoken refreshn(`CSRF tonsole.war          c= error;
tError las
          ) {error (catch       } ;

 Text}`)${error}: atusonse.st{respor(`HTTP $ew Errhrow n      t
    nse.text(); respo= awaitext nst errorT    co
      ssfulasn't succeesponse we, the r here get If w    //             }

 }
            token;
  f_.csreturn data    r
          y');uccessfullhed s refres('CSRF tokenonsole.log   c      ;

     })            
  en;f_tok = data.csrt.value    inpu           {
  put =>inch(puts.forEanIn        toke
      ]');f_tokene=csrnput[namectorAll('ient.querySel documkenInputs =   const to   ts
        puindate form   // Up       
       }
          ewMeta);
  endChild(n.appheadocument.    d            en;
rf_tok= data.cscontent eta.      newM     ;
     f-token'csr 'wMeta.name =    ne           );
 ement('meta'eateElcr document. newMeta =  const          ist
    t exn' it doesmeta tag if/ Create        /         } else {
             
 n);ke.csrf_totantent', dae('cotributAtTag.set meta    
           ) {(metaTag    if   
        ');-token][name=csrfmetaor('.querySelectentumaTag = doct met      cons        e meta tag
at  // Upd        
    en) {f_tokdata.csrif (         
   nse.json();poawait rest data = ons  c        k) {
  (response.o    if 

      ;    })
                }che'
  a': 'no-ca'Pragm              cache',
o-Control': 'ne-ch   'Ca      rs: {
     eade        hn',
    -origisames: 'ntialrede           c: 'GET',
      method      , {
 csrf-token'ch('/get-await fetresponse =      const    `);

  xRetries}t}/${mapt ${attempsh attemn refreCSRF tokeonsole.log(`          c   try {

     t++) {ries; attempRet= maxtempt <pt = 1; att attem    for (le null;

  or =let lastErr;
      ies = 3trst maxRe  con) {
    ction (ync funen: ashTokefres r
      */y logic
  ng and retrdlior hanmproved errth i token wih CSRF* Refres  /**
     
  
  csrf: {ten managemenF tok
  // CSR },
);
    }
 durationtype, st(message, ls.showToamGrader.uti
      Exa
      }
   return;;
     ${message}`)type} - l()}): ${icationLeve.getNotif: ${thisd (levelon suppresseati(`Notificle.log    conso{
    (type)) otificationowNouldSh!this.sh if (00) {
     uration = 50'info', d = age, typeesson (mify: functi notria
   iteerence cruser's prefhe eets ttion if it mhow notifica

    // S },   
e;
      }trurn   retu:
           defaultall':
      '        case;
rning'wa === 'ror' || type 'er ===return type        :
  t'mportan    case 'irror';
    === 'en type       returrs':
    ase 'erro        c
alse;    return f  one':
      case 'n) {
      eltch (lev  swi

    l();ficationLevetNotige = this.t level     constype) {
 nction (ation: fu