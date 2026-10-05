"""Convert retained internal-domain test fixtures to the new model-only DTO.

Used only by older tests constructing approved domain originals. Product authors
never accept or convert these old wire contracts. Boundary tests use raw wires.
"""
import copy


def model_dto(body):
    v=copy.deepcopy(body)
    if isinstance(v,dict) and 'work' in v and ('scene' in v or 'scenes' in v):
        sample=v['scene'] if 'scene' in v else v['scenes'][0]['scene']
        if sample.get('subjects') and 'id' not in sample['subjects'][0] and all('speakerSelection' in d for d in sample.get('dialogue',[])):return v
        def scene(s):
            roster=list(dict.fromkeys(d['speaker'] for d in s.get('dialogue',[]))) or ['traveler']
            return {'sceneText':s['sceneText'],'subjects':[{'name':n,'meaning':'Canonical source participant.'} for n in roster],
                'dialogue':[{**{k:x for k,x in d.items() if k not in {'id','speaker'}},'speakerSelection':roster.index(d['speaker'])} for d in s.get('dialogue',[])]}
        if 'scene' in v:v['scene']=scene(v['scene'])
        else:v['scenes']=[{'scene':scene(s['scene'])} for s in v['scenes']]
    elif isinstance(v,dict) and 'shots' in v:
        scenes=list(dict.fromkeys(s['sceneId'] for s in v['shots']))
        shotids=[s['shotId'] for s in v['shots']]
        v={'shots':[{'sceneSelection':scenes.index(s['sceneId']),'shot':model_dto(s['shot']),
            'requiresSelections':[shotids.index(x) if x in shotids else 99 for x in s.get('requires',[])],
            'transition':s.get('transition','cut')} for s in v['shots']]}
    elif isinstance(v,dict) and 'spokenIds' in v and 'professionalDomains' in v:
        v['spokenSelections']=[0 if x=='appeal' else 99 for x in v.pop('spokenIds')]
    elif isinstance(v,list):
        for row in v:
            if not isinstance(row,dict) or 'facts' not in row:continue
            facts=row['facts']; domain=row.get('domain')
            if domain=='PERFORMANCE' and 'beats' in facts:
                ids=[b.get('id') for b in facts['beats'] if isinstance(b,dict)]
                def beat(x):return ids.index(x) if x in ids else 99
                for b in facts['beats']:
                    if 'actor' not in b:continue
                    b['actorSelection']=0 if b.pop('actor')=='traveler' else 99
                    b['targetSelection']=0;b.pop('target',None);b.pop('id',None)
                for line in facts.get('lines',[]):
                    if 'spokenContentId' in line:line['spokenSelection']=0 if line.pop('spokenContentId')=='appeal' else 99
                    if 'beatId' in line:line['beatSelection']=beat(line.pop('beatId'))
                for s in facts.get('projectionSubjects',[]):
                    if 'subjectRef' in s:s['subjectSelection']=0 if s.pop('subjectRef')=='traveler' else 99
                    s.pop('sourceTargetLabel',None);s.pop('spokenIds',None)
                    if 'beatIds' in s:s['beatSelections']=[beat(x) for x in s.pop('beatIds')]
            elif domain=='ACTION':
                for row in facts.get('actionPhases',[]):
                    row['beatSelection']=0;row.pop('beatId',None);row['spokenSelections']=[0 if x=='appeal' else 99 for x in row.pop('spokenIds',[])]
            elif domain=='SUBJECTS':
                for row in facts.get('presentSubjects',[]):row.pop('id',None);row['subjectSelection']=0
            elif domain=='REFERENCE':
                for row in facts.get('references',[]):row.pop('id',None);row['beatSelections']=[0 for _ in row.pop('beatIds',[])]
    def targets(x):
        if isinstance(x,dict):
            if 'interactionTarget' in x:x.pop('interactionTarget');x['interactionTargetSelection']=0
            for child in x.values():targets(child)
        elif isinstance(x,list):
            for child in x:targets(child)
    if isinstance(v,list):targets(v)
    return v
