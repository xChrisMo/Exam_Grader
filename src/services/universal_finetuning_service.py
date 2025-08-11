"""
Universal Fine-Tuning Service

This service provides fine-tuning capabilities across different LLM providers
including OpenAI, DeepSeek, Anthropic, and others.
"""

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests
from src.services.base_service import BaseService
from utils.logger import logger


class FineTuningProvider(Enum):
    """Supported fine-tuning providers."""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    UNSUPPORTED = "unsupported"


@dataclass
class FineTuningJob:
    """Fine-tuning job information."""
    job_id: str
    provider: FineTuningProvider
    model_name: str
    status: str
    training_file_id: Optional[str] = None
    validation_file_id: Optional[str] = None
    fine_tuned_model: Optional[str] = None
    created_at: Optional[int] = None
    finished_at: Optional[int] = None
    error: Optional[str] = None
    hyperparameters: Optional[Dict] = None


@dataclass
class TrainingData:
    """Training data for fine-tuning."""
    messages: List[Dict[str, str]]
    metadata: Optional[Dict] = None


class FineTuningProvider(ABC):
    """Abstract base class for fine-tuning providers."""
    
    @abstractmethod
    def supports_finetuning(self) -> bool:
        """Check if the provider supports fine-tuning."""
        pass
    
    @ab()erviceeTuningSinlFUniversa= g_service tuninineiversal_fun instance
ice servGlobal

# n models
etur   r         
   ue] = []
 alls[prov.v     mode            
   v}: {e}")or {promodels ft listo (f"Failed gger.warning          lo    e:
      n as  Exceptioept       exc    ls()
     deinetuned_mov].list_fpro.providers[lue] = selfs[prov.vaodel m                 try:
                  
.providers:n self if prov     i      k:
 checrs_to_roviderov in por p       f 
 ()
       iders.keysrov else self.poviderer] if provid= [pr_to_check viders
        pro       {}
 ls =     mode"
    dels.""ned moe-tuailable fin avllt a   """Lis  
   :tr]] List[sict[str, Dr = None) ->ngProvideneTuniovider: Filf, prs(seble_modellist_availa    def 
   )
 e"availabler} not ovidProvider {prueError(f"ise Val      raid)
  job_ob_status(t_jr].ge[provideders.provielfn stur       re:
     rsrovide self.provider in   if p""
     atus."uning job stne-t"""Get fi       
 eTuningJob:der) -> FingProvir: FineTunin provideid: str,, job__status(selfob get_j    def
    
"local")r, videlts.get(pro defauturn
        re       }ocal"
  "l.LOCAL:iderneTuningProv   Fi     ",
    eepseek-chat: "dEEPSEEKngProvider.D FineTuni         ",
  bo3.5-turgpt-ENAI: "ovider.OPTuningPr      Fine
      = {s    default     "
""rovider.model for pault """Get def   
     r: str) ->uningProvide FineTprovider:f, odel(selt_mulget_defa  def _
    
  raise      ")
       {e}ng failed:ine-tunior(f"F logger.err
           on as e:t Excepti    excep   
  
           eturn job      r    ")
  er}providder {ith provib.job_id} wing job {jofine-tun"Started (ffo.inogger      l      
  
                )      
ider)odel(provefault_m._get_d self    model or           g_file, 
 nin       trai         g_job(
e_finetunincreats[provider].oviderelf.prjob = s     job
       uning  fine-trt    # Sta              
 
     amples)training_exta(raining_daare_tvider].prepers[proidlf.prov_file = seiningra        tuides)
    ing_gdes(trainm_guifroa_datining_te_traeaes = self.cr_examplraining        tta
     dangraini# Prepare t      
             L
     LOCAingProvider.neTunovider = Fi   pr            ")
 lback to locafalling g, t fine-tuninor supp} doesn'tr {providerrovide"P.warning(flogger               vider):
 ronetuning(p.supports_fielfot s       if n         
    )
    able"ailr} not avideider {provProvor(f"eErrValu raise           ers:
     elf.providin st rovider no        if p    
           ase_url)
 nt_bey, curre_api_kntreprovider(curself.detect_rovider =   p         )
      ""SE_URL",M_BA("LLtenvrl = os.ge_base_uent     curr         
  API_KEY")"OPENAI_tenv( or os.ge_KEY")EEK_API"DEEPSos.getenv(api_key = t_ curren               r is None:
rovide      if pd
      ecifieif not spder rovidetect p # Auto-           :

        tryess."""oce-tuning pr fin """Start     
  ningJob:e) -> FineTu Nonmodel: str =er = None, vidingProder: FineTunDict], proviides: List[aining_gug(self, trnintart_finetudef s
    
    plesexam training_ return      
 )
        pend(example.ap_examples training                      }
        , '')
 ia'iterion.get('cr": questeriaoring_crit"sc                   e', 10),
 scor.get('max_": questionre    "sco          
      ",')}
""iteria.s all cret that me answerntleack', 'Excel_feedbmplet('saion.gequestdback: {0)}/10
Feecore', 1n.get('max_s: {questioScore"
"f"sponse": ed_re"expect          
          
""",ack.vide feedbwer and proans
Grade this ]
EHOLDERACWER_PL[STUDENT_ANSwer: dent Ans10)}
Sture', max_scostion.get(' {que Score:
Maxia', '')}erget('crit{question.: teriaing CriMark')}
 't('text',geon.esti: {qustion""
Quet": f"er_promp "us                   a.",
g criterirkine maording to thswer accollowing an the frader. Gradet exam gre an exper a: "You"stem_promptsy"         
           ple = {       exam     ions:
    n questestion i      for qu      
       [])
      ",sonquestiet("s = guide.g   question         guide
 from ted answersexpecstions and ueExtract q        # ides:
    _gu training guide in      for
  
        es = []xampl  training_e   ."""
   ning formattuo fine- guides ttrainingonvert ""C
        "st[Dict]:-> Liist[Dict]) g_guides: Lraininelf, tm_guides(s_frong_dataainif create_tr    
    dealse
n F   retur()
     etuninginrts_f].suppo[providerlf.providersreturn se           
 viders:lf.proin sevider    if pro    ng."""
 s fine-tunir supportovide if a prheck"""C       bool:
 ovider) -> eTuningPr: Fin, providertuning(selfs_fineortdef supp 
      CAL
 .LOgProvidern FineTunin retur       
        
PSEEKDEEer.gProvidneTunin return Fi        ():
   key.loweri_ap in eepseek"    elif "d    PENAI
gProvider.O FineTunin   return   
      k-"):"sstartswith(key.api_     if mat
   forPI key  A fromtecto de Try t      #        
  ROPIC
rovider.ANTHeTuningPeturn Fin           r
     _url:sem" in ba.coopic"anthr    elif EK
        der.DEEPSEuningProvineTrn Fi      retu     _url:
     " in baseeek.com"deeps      elifI
       ider.OPENAovTuningPrne  return Fi             
 base_url:om" in f "openai.c          i_url:
  if base             
  r.LOCAL
 ideeTuningProveturn Fin        r    pi_key:
 a  if not   
   URL."""API key and sed on used bag  is beinoviderh prtect whicDe """      r:
 ingProvideTun> Fine) -: str = Nonease_url str, bapi_key:ider(self, etect_prov   def d")
    
 )}ys()providers.kef.(selrs: {listdevironing ped fine-tu"Initializr.info(f     logge    
   der()
    ProviTuning = LocalFineLOCAL]gProvider.ineTuninoviders[Flf.pr      se
  ble)ways availacal (al        # Lo  
      k_key)
er(deepseeProvidTuningSeekFine] = DeepPSEEKovider.DEEgPrineTunin[Fiders   self.prov
         y:eepseek_keif d    Y")
    SEEK_API_KEDEEP"s.getenv(_key = oek deepsek
       # DeepSee 
             
  i_key)openaovider(gPrnineTuOpenAIFinENAI] = Provider.OPningders[FineTuvi   self.pro:
         enai_keyop
        if _KEY")APIPENAI_v("O= os.geteney penai_kI
        o # OpenA
       ."""ng providersine-tunilable ftialize avai""Ini      "self):
  viders(alize_proiniti
    def _    roviders()
itialize_p  self._in}
       {roviders =      self.pice")
  rvnetuning_seal_fi"univers(__init__per().
        su__(self):_initef _
    d""
    rs."e providetipl mulworks withe that ervic-tuning sfine"Universal ":
    "ce)rviSeaseingService(BrsalFineTuns Unive

clas_files]
mptn pro i f" for.')[0]}].split('[-1')(f).split('_basename_{os.path.[f"localn tur    re")
    mpts_*.jsonromized_p("temp/optib.globles = glo  prompt_fi
      lob g  import     t files
 rompized poptimvailable    # List a     ""
dels."uned mol fine-t"List loca     ""
    List[str]:elf) ->ed_models(st_finetunf lis
    de )
    d"
       mplete="cotus     sta  
     "local",me=na  model_
          OCAL,vider.LngPro=FineTuniider       prov   =job_id,
  _id         jobJob(
   neTuning   return Fi   ""
  tus."ng job stafine-tunil et loca"""G      
  TuningJob:r) -> Fineob_id: st(self, jt_job_statusf ge    deompt
    
stem_prsyn       retur        
  s."""
urate scored accck and feedbaetailee dns. Providese patterd on thasesistently b and con fairly""
Grade"m_prompt +=    syste   
     "
     0]}...\n:10dicator["- {in= f_prompt +      system    ])[:3]:
   [",dicators_score_inget("lowterns.or in patr indicat    fo     
      
 n"CATORS:\DIOW SCORE IN"\nLpt += m_prom   syste    
        
 0]}...\n"dicator[:10"- {inpt += fprom  system_          , [])[:3]:
indicators"e_scorhigh_s.get("ttern painor r indicat        fo       

"""
  INDICATORS:RE
HIGH SCOdelines:
 guiow theseoll, fded data proviningraie t Based on thgrader.t exam  an experYou aret = """tem_promp     sys
         {})
  s", tternse.get("paedge_bas = knowl  pattern
      ""."ng dataini tra based onem promptzed systn optimirate a"Gene""
        ) -> str:: Dictedge_base knowlrompt(self,te_system_pgenera    def _ 
nt=2)
    f, inde_prompts,optimized.dump(  json          f:
w') as pts_file, '(prom  with open 
                  }
ria"]
   crite"scoring_ge_base[": knowledriacriteing_or    "sces
         examplse top 5:5],  # U"]["examplesdge_base[ knowle":amplesgrading_ex       "ase),
     dge_bnowlet(kompe_system_prenerat": self._gomptm_prtesys  "          s = {
promptized_      optim 
  n"
       _id}.jsoobd_prompts_{jimizep/optile = f"temts_f promp       se
r later us fomized prompt# Save opti        """
ning data.on traimpts based ed proeate optimizCr   """   tr):
  b_id: sjo Dict, e:basge_nowledf, kompts(seld_prizeate_optimf _cre    
    de )
      ())
 .timeimeat=int(t finished_           e.time()),
=int(tim_at  created  
        d",te"comple    status=     ,
   odel=m  model_name       LOCAL,
   rovider.gPr=FineTunin    provide       ,
 b_id=jo_id     job(
       ngJobn FineTuni    retur           
job_id)
 ge_base, leds(know_prompt_optimizedeateelf._cr
        sta training dabased onts prompd izeCreate optim  # 
             
 d(f)n.loae_base = jso knowledg   :
         fr') ase_path, 'training_fil  with open(a
      dat training rocessd and p     # Loa   
       )}"
 ime()t(time.tlocal_{injob_id = f"       ""
 )."zationpt optimireally promob (tuning' je-inl 'freate a loca"C"":
        ineTuningJobgs) -> Far, **kwl"= "loca str  str, model:h:ing_file_pat(self, traintuning_jobte_finef creade   
    riteria
 return c     "])
   ariteri_c["scoring(examplenderia.appe     crit    e:
       " in exampliang_criter if "scori          xamples:
 example in e       for  []
 ia = criter       ""
ples."from examcriteria ing  scor"""Extract    t]:
    > List[Dic[Dict]) -mples: List exaf,seliteria(crct_scoring__extra  def   s
    
urn pattern  ret
         se)
     esponnd(rs"].appere_indicatorow_scopatterns["l             3:
   ore <=   elif sc
          response)ppend(icators"].ascore_indh_tterns["hig    pa     :
       = 8re >sco   if 
                   "")
  , response""expected_xample.get(response = e            
0)re", .get("scoamplee = ex       scor  mples:
   xa in eplexam for e   
        }
      []
       riteria":rading_c        "g
    takes": [],on_mis"comm       
     ": [],icators_ind"low_score    ,
        ": []dicatorsscore_in     "high_      {
  atterns =  p     ."""
 plesexaming  from trainternsaton pcommtract   """Ex:
      t]) -> Dict[Dicples: Listexamerns(self, act_patt _extr  
    defpath
  le_ fi      return    
  
    t=2) f, indenbase,owledge_ump(kn json.d         f:
   , 'w') asile_pathith open(f    w  
      =True)
    exist_okmp", edirs("te    os.mak   
 n".jsotime())}_{int(time.raining/local_tth = f"tempe_pa     fil       
        }
 
   s)ing_exampletrainiteria(ing_cract_scortrelf._ex sria":ing_crite "scor     
      xamples),ning_eerns(trai_pattextractlf._erns": se"patt          mples,
  ining_examples": traxa       "e   
  = {e _baswledge      kno
  xamplesining eom tra fraseowledge b kn# Create a      
  """neering.engimpt local prong data for traini"Prepare     ""
    str:ict]) -> ples: List[Dg_examf, traininata(sel_training_d preparedef    
    ue
urn Tr   ret  
   lf) -> bool:tuning(ses_finertef suppo
    
    ds        paslf):
__init__(seef   d    
  g."""
earnin land few-shotgineering ompt eng prg usinne-tuninl fi """Loca):
   derngProvieTunir(FinngProvideunilFineTs Loca
clasn []

etur"
        r.""ed modelsek fine-tuneepSe""List D       "[str]:
  -> Listmodels(self)inetuned__f  def list  
  ")
   neededtionk implementa status checingunfine-tDeepSeek dError("menteNotImple    raise 
    ""atus."ng job st-tunieek finet DeepS  """Ge:
      neTuningJobtr) -> Fi: sb_idf, jo(seltatusb_sef get_jo    
    dd")
detion neeimplementang API fine-tunik r("DeepSeerrontedEememplotIise N      ra
   API DeepSeek'sonnds on depemplementati ier - actualholda placehis is        # T
 ointsek endpith DeepSeut wI bpenAimilar to Oementation s    # Impl"""
    pported).g job (if sufine-tuninepSeek "Create De""        TuningJob:
nes) -> Fikwarg **k-chat", = "deepsee: strtr, modelfile_path: sf, training_ning_job(seltuine_freate   def ces)
    
 g_examplnina(traiaining_dat).prepare_trelf.api_keyovider(singPrneTunAIFi Openrn      retu"
  format).""enAI  Opilar toepSeek (sim data for Deare training""Prep     "   str:
 ict]) -> List[Damples:training_exelf, ining_data(stradef prepare_  
      alse
 return F         pt:
          exce404
!= ode _cstatusponse.res   return     
           )
      eaderslf.hs=se    header     ,
       s"obtuning/jine__url}/f"{self.base   f          .get(
   tsrequessponse =       re
      try:     vary)
    his may-tuning (tfineek supports if DeepSe   # Check :
     bool-> g(self) etuninports_findef sup 
       }
   
     /json"cationapplipe": ""Content-Ty           ",
 pi_key}"Bearer {a: fhorization""Aut     {
       eaders = elf.h      som/v1"
  deepseek.ci./ap= "https:/url se_     self.baapi_key
   f.api_key = el
        skey: str): api_lf,_(set__inidef _
      ""
  ation."mplementning ituepSeek fine-"""Deder):
    uningProvider(FineTingProviTuniness DeepSeekF]


clad_model")ne_tuneob.get("fiobs if jn j job iord_model"] f["fine_tuneturn [job
        rea", [])"datn().get(nse.jsoespo = r        jobs       
[]
 turn re     :
       ode != 200status_c response.      if
            )
  s
    f.headeraders=sel  he          jobs",
ne_tuning/rl}/fif.base_u  f"{sel
          quests.get(se = respon        res."""
deled monAI fine-tunpet O"""Lis:
         List[str]->s(self) uned_model list_finet   
    def
 
        )else None") roret("erjob_info.gage") if ss"met(}).ge {"error",info.get(b_=joor        err),
    hed_at"iso.get("finjob_inffinished_at=          t"),
  created_a"o.get(inf=job__at     created   
    el"),odd_mune("fine_tb_info.getdel=jomofine_tuned_           
 atus"],fo["stjob_inatus=  st          model"],
o["b_inf_name=jo     model
       ENAI,vider.OPineTuningProovider=F    pr       
 o["id"],infid=job_b_      jo      b(
TuningJoreturn Fine)
        n(onse.jso_info = respjob 
        
       t}")exonse.t{respjob status: led to get on(f"Faiptixce   raise E
         200:ode != _ctusse.sta   if respon     
        
     )ers
   ad=self.he    headers     _id}",
   jobs/{jobine_tuning/base_url}/ff"{self.         get(
    = requests.sponsere"
        us."" statjobing tunI fine-enAGet Op """
       ob:FineTuningJstr) -> b_id: f, jo(selb_statusget_jof     dee
    
     rais      {e}")
 led: ation fai job cre fine-tuningAIOpen.error(f"      loggere:
       as eptionxcept Exc
        e        
           )at")
     created__info.get("t=jobeated_a         crd,
       ile_ile_id=fing_fi   train            ],
 "status"_info[=job status          el,
     name=mod    model_            
AI,vider.OPENuningProder=FineT  provi             id"],
 ["_id=job_info         jobob(
       gJin FineTunreturn            .json()
 = response job_info               
  
      e.text}")respons job: { fine-tuningtecrea"Failed to fn(eptio raise Exc                200:
 !=us_codese.statsponif re            
           )
      
       ata json=job_d       ,
        self.headersaders=         he      
 ng/jobs",nine_tuurl}/fi.base_f"{self                s.post(
estqure =    response
                          }
  
     ters", {})ramerpa("hype kwargs.getrs":rparameteype   "h            
 ": model,del        "mo,
        e_id_file": filngaini "tr          
     job_data = {         ng job
   ni fine-tu# Create                  
 d"]
     ["i()nse.jsonespo file_id = r                  
  )
   se.text}"on{respining file:  tra to uploadon(f"Failed Excepti raise               != 200:
e tatus_codse.sponf res      i
                 
          )   
    esles=fil        fi          key}"},
  f.api_arer {selBeon": f"horizatis={"Auteader   h               iles",
  l}/f_urf.basef"{sel                   .post(
 questse = re    respons            tune")}
"fine-: (None, "purpose"ile": f,  = {"f       files   
      rb') as f:ath, 'file_png_ainith open(tr wi  
         leng fipload traini       # U try:
           ""
 ning job."nAI fine-tueate Ope """Cr   Job:
     FineTuningrgs) ->kwao", **5-turb = "gpt-3.el: str: str, modpathg_file_ninlf, traiseob(uning_jnetcreate_fi    def   
ath
  ile_p   return f   
     
      + '\n')(item)on.dumps(jsf.write                ing_data:
intem in tra     for i
       as f:ath, 'w') pen(file_pwith o     
       
    ist_ok=True)emp", ex"t.makedirs(    os"
    jsonl)}.(time.time()_{intainingenai_trf"temp/ople_path = fi        JSONL file
  # Save as        

       s})essagees": magnd({"messata.appe_dining  tra  ]
              }
      "), "onse"sp"expected_re(xample.gettent": e "contant","assis": role   {"            ")},
 "prompt", er_le.get("usexamp": "content, "user"ole":        {"r         ms.")},
 exaing grad forl assistantelpfuu are a h"Yo_prompt", ystem"sget(example.nt": ", "conte"system":     {"role           sages = [
        mes     format
t I chapenArt to O  # Conve  s:
        ampleaining_exle in trexamp    for      
     []
   ning_data =rai        tmat."""
's JSONL forn OpenAI iining data"Prepare tra"      "
  -> str:t[Dict]) es: Lisampling_exlf, trainning_data(see_traif prepar  de
    
  eeturn Tru
        rl:boo -> ng(self)tuniupports_fine
    def s    }
    json"
    cation/appli": "-Typent   "Conte
         pi_key}",earer {a": f"Bonzatithori   "Au      
   eaders = {  self.h
      .com/v1"penai/api.ohttps:/ "ase_url =self.b    pi_key
     alf.api_key =      sey: str):
  i_ke__(self, ap def __init
    
   n."""io implementatng fine-tunienAI   """Opder):
 ningProvir(FineTuProvideIFineTuningass OpenAcls


  pas  
    """ned models.ne-tuvailable fiist a""L "
       ist[str]:s(self) -> Luned_modelist_finet  def lhod
  etctm @abstra
   
    ss      pa
  "b.""uning joe-t a finof status ""Get the
        "TuningJob:tr) -> Fine s job_id:elf,us(sstatdef get_job_
    ctmethod
    @abstraass
            p"
ob.""tuning jeate a fine-   """CrJob:
     ingineTun -> F, **kwargs)del: strr, moth: stning_file_patraielf, g_job(s_finetunineate   def crmethod
    @abstract
   ss
    pa""
      ."der's formatprovi the a inat training dare  """Prep     tr:
 ) -> sct]Dit[mples: Lisexang_ trainita(self,ng_da_trainiepare
    def prstractmethod