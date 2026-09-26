"""TECHNICAL_FIXTURE: wholly synthetic source; no formal screenplay or media."""
import hashlib
from drama_plugin.contracts.creative_source import LiteraryPackage
from drama_plugin.creative_source import review_hashes


def fixture():
    text = '林在雨停后收起门边的空碗。她想敲邻居的门，手却停在半空。\n\n傍晚，邻居将一只干净的碗放回门边。林打开门，把两只碗摆在一起。'
    rights = dict(status='USER_OWNED', jurisdictions=['TEST'], evidence=['synthetic fixture author record'], assertedBy='test-author', basis='PROVENANCE_RECORD', permittedUses=['ADAPTATION', 'COMMERCIAL_PRODUCTION'])
    kinds = [('c', 'CHARACTER', '林'), ('e1', 'EVENT', '收碗后停手'), ('e2', 'EVENT', '摆出两只碗'), ('object', 'OBJECT', '碗'), ('internal', 'INTERNAL_STATE', '想敲门'), ('relation', 'RELATIONSHIP', '邻居关系')]
    units = [dict(id=i, kind=k, origin='SOURCE_FACT', statement=t, anchorIds=['a'], supports=[], characterIds=['c']) for i,k,t in kinds]
    units.append(dict(id='interpretation', kind='CONFLICT', origin='INTERPRETATION', statement='可能在迟疑与接近之间摇摆', anchorIds=['a'], supports=['e1','e2'], characterIds=['c']))
    absent = {k: 'tiny fixture does not establish a separate unit' for k in ('POV','CHRONOLOGY','NARRATOR','SETTING','MOTIF','IMAGE','ARC','SCENE','STRUCTURE')}
    data = dict(sourceType='LITERARY', id='synthetic-only', artifacts=[dict(id='original', title='两只碗（结构测试）', kind='ORIGINAL_TEXT', role='SOURCE_OF_TRUTH', provenance='Original technical fixture written for P0; no external work', text=text, textSha256=hashlib.sha256(text.encode()).hexdigest(), rights=rights)], sourceArtifactId='original', anchors=[dict(id='a',artifactId='original',start=0,end=len(text),quote=text)],
        analysis=dict(units=units,eventOrder=['e1','e2'],chronology='同一天',narrativePov='第三人称',narrator='未具名叙述者',narrativeStructure='两个动作阶段',absentCategories=absent),
        philosophicalCore=dict(sourceUnitIds=['e1','e2'],question='迟疑是否阻止接近？', conflict='保留距离与试探接近',valuePoles=['距离','接近'],characterChoice='摆碗',consequence='距离有变化',ambiguity='意图仍未知'),
        adaptation=dict(preserved=dict(mustKeep=['e1','e2'],coreRelationships=['relation'],coreEvents=['e1','e2'],characterArc='迟疑到试探',themeConflict='距离与接近',narrativeIdentity='两个门边动作'), permittedChanges=['KEEP','EXTERNALIZE'], decisions=[dict(id='d',operation='EXTERNALIZE',sourceUnitIds=[u['id'] for u in units],reason='保留动作并让迟疑可见',narrativeEffect='动作而非解释',expression='手部停顿与摆碗')]),
        compression=dict(mappings=[dict(decisionId='d',destinationIds=['beat:test'])]),
        cinema=dict(expressions=[dict(id='x',decisionId='d',destinationId='beat:test',channels=['ACTION','SILENCE'],shootableExpression='停手；摆碗',choiceActionConsequence='先停下，后摆出第二只碗',nonverbalAlternative='停顿与空间距离')]),
        characterArc=dict(states=[dict(characterId='c',arcStage=stage,sourceUnitIds=[unit],origin='INTERPRETATION',narrativeState=n,emotionalState='未明确',beliefState='未明确',behavioralState=n,relationshipState='邻居',performanceImplication=n,visualContinuityBoundary='同一角色身份；不决定外貌') for stage,unit,n in [('early','e1','停手'),('late','e2','摆碗')]]),reviews=[dict(authority=a,subjectHash='0'*64,status='APPROVED',reviewer='fixture-reviewer',evidence='structural test only, not artistic acceptance') for a in ('literary-source-analysis','philosophical-core','literary-adaptation','literature-to-cinema','character-dramaturgy')])
    return reviewed(data)


def reviewed(data):
    # Explicit synthetic preservation attestation, never applied to real sources.
    protected = data['adaptation']['preserved']
    keys = set(protected['mustKeep'] + protected['coreRelationships'] + protected['coreEvents']) | {'character_arc','theme_conflict','narrative_identity'}
    for review in data['reviews']:
        if review['authority']=='literary-adaptation':
            review['preservationChecks']={key:dict(status='PRESERVED',sourceUnitIds=[key] if key in {u['id'] for u in data['analysis']['units']} else ['e1','e2'],
                destinationIds=['beat:test'],evidence='Synthetic source preserves the hesitation, neighbor relation and later bowl arrangement.') for key in keys}
    p = LiteraryPackage.model_validate(data)
    for review in data['reviews']:
        review['subjectHash'] = review_hashes(p)[review['authority']]
    return data
