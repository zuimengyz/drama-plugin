"""Synthetic portable package fixture. No project or historical character content."""
from datetime import datetime,timezone
from drama_plugin.contracts.character_package import CharacterDesignAuthorization
from drama_plugin.characters.authoring import create_character_version
from drama_plugin.characters.repository import CharacterRepository,digest
from drama_plugin.contracts.base import dump_contract

def make_package(root,version='v1',status='DRAFT',identity='Synthetic actor'):
    root.mkdir(parents=True,exist_ok=True);(root/'source.md').write_text('Approved synthetic screenplay')
    now=datetime.now(timezone.utc).isoformat(); directive=b'Create synthetic draft versions.'
    data={'manifest':dict(packageId='test.actor',characterId='actor',projectId='synthetic',version=version,status=status,createdAt=now,updatedAt=now,sourceWork='w',sourceRevision='r',sourceFingerprint=digest((root/'source.md').read_bytes()),supportedRoutes=['heroic_cinematic_cg'],publisher='test',license='private-test',authors=['fixture'],compatibility={'contract':'v1'},dependencies=[],checksum='0'*64,fileChecksums={}),
    'core':dict(identity=identity,historicalRole='Fictional worker',lifeStage='Midlife',dramaticRole='Witness',personalityCore=['Counts costs before agreeing'],desire='Keep a promise',fear='Fail a dependent',belief='Promises carry costs',contradiction='Duty competes with escape',decisionPattern='Checks before committing',dramaticArc='Reluctance becomes responsibility'),
    'dramaticIdentity':dict(authorialStatement='A promise matters because escape is possible.',selfImage='Reliable',socialPosition='Worker',pressure='Time',distinctiveChoices=['Waits for another'],sameArchetypeComparisons=[dict(comparator=x,sharedArchetype='witness',distinction='This person waits',sourceBasis='fictional comparison') for x in ['impatient observer','indifferent observer']]),
    'visualExpression':{'routes':{'heroic_cinematic_cg':dict(visualRoute='stylized_cinematic_cg',visualLanguage='HEROIC_CINEMATIC_CG',proportionPolicy='GROUNDED_DESIGNED',performancePolicy='CG_AUTHORED',equipmentPolicy='FUNCTIONAL_GROUNDED',cameraPolicy='Scene owned',designIntent='Working identity',identityAnchors=['Attentive hands'])}},
    'actionSignature':{**{k:'Deliberate and grounded' for k in ['movementCharacter','decisionTempo','powerSource','weaponRelationship','mobilityStyle','combatRhythm','recoveryStyle']},'forbiddenDrifts':['New powers'],'eventBoundary':'Script only'},
    'performance':dict(baseline='Attentive',states={'listening':'Wait','pressure':'Recheck','silence':'Watch'},relationalVariations={},continuityLimits=['Retain injuries']),
    'dialogueVoice':{**{k:'Concise and practical' for k in ['sentenceForm','lengthAndExplanation','directness','rhetoric','emotionalExposure','powerLanguage']},'relationalVariations':{},'providerBinding':'UNBOUND'},
    'antiDrift':dict(avoid={'generic':'Preserve decision pattern'},reviewTests=['Check unnamed choices']), 'relationships':{'edges':[]},
    'historicalBasis':dict(documentedFacts=[],strongInferences=[],artisticInterpretations=['Fictional'],uncertainElements=['Appearance'],sourceRefs=['source.md']),
    'provenance':dict(sourceWork='w',sourceFiles={'source.md':digest((root/'source.md').read_bytes())},historicalSources=[],host='test',createdAt=now,revision=version,userFeedback=[],referenceAssets=[],license='private-test',authorshipBoundary='Synthetic',approvalEvidence=[])}
    auth=CharacterDesignAuthorization(capability='character-external-driver',sourceWork='w',sourceRevision='r',directiveRef='test',directiveHash=digest(directive),allowedPackageRefs=['characters/synthetic/actor'])
    repo=CharacterRepository(root);p=create_character_version(repo,data,authorization=auth,directive=directive)
    ref={'characterPackageRef':'characters/synthetic/actor','characterPackageVersion':version,'checksum':p.manifest.checksum}
    return repo,p,ref,auth,data
