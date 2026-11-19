"""Raw-account integer oracle for the focused proposed Devnet profile. No VM/producer imports."""
import struct

U64=(1<<64)-1
SYSTEM='11111111111111111111111111111111'
CAPACITY=3_000_000_000_000_000
REFILL=50_000_000_000_000
BINDING=bytes.fromhex('aab3babb1be2805158cf9d1c52b6b55a8aa0ccf657e92dc863ce1150f837dbb9')

def amount(raw,offset):return struct.unpack_from('<Q',raw,offset)[0]

def raw(record):return bytes.fromhex(record['data_hex'])

def replace_u64(data,offset,value):
    assert type(value)is int and 0<=value<=U64
    result=bytearray(data);struct.pack_into('<Q',result,offset,value);return bytes(result)

def extension(raw,kind):
    assert len(raw)>165
    pos=166;found=None;seen=set()
    while pos<len(raw):
        if not any(raw[pos:]):break
        assert pos+4<=len(raw)
        tag,size=struct.unpack_from('<HH',raw,pos);pos+=4
        assert tag not in seen and pos+size<=len(raw);seen.add(tag)
        if tag==kind:assert found is None;found=(pos,size)
        pos+=size
    assert found is not None
    return found

def token(data):
    assert len(data)>=165
    if len(data)==165:return amount(data,64),0
    pos,size=extension(data,2);assert size==8
    return amount(data,64),amount(data,pos)

def volume(data):
    assert len(data)==89 and data[:10]==b'HTFPVOL1\x01\x00' and data[11:43]==BINDING
    assert data[67]<=1 and data[80:]==bytes(9)
    return dict(credit=amount(data,43),last=struct.unpack_from('<q',data,51)[0],sequence=amount(data,59),active=data[67],nonce=amount(data,72))

def rounding_up(n,d):
    result=(n+d-1)//d
    assert result*d>=n and (result==0 or (result-1)*d<n)
    return result

def quote(q,x,y,epoch):
    assert 0<q<=U64 and q%8==0 and 0<x<=U64 and 0<y<=U64
    burn=3*(q//8);gross=5*(q//8)
    tax=rounding_up(gross*8,100)if epoch>=1210 else 0
    net=gross-tax;fee=rounding_up(net*5,1000)
    creator=fee//2;trade=fee-creator;curve=net-fee
    output=curve*y//(x+curve)
    assert output*(x+curve)<=curve*y<(output+1)*(x+curve)
    return dict(burn=burn,gross=gross,tax=tax,net=net,creator=creator,protocol=trade*12//100,fund=trade*4//100,output=output)

def effective(pool,vault,side):
    debt=sum(amount(pool,off+side*8)for off in (341,357,397))
    assert debt<vault
    return vault-debt

def observation(data,now,wsol,htfp):
    """Independently recompute the official fixed pool's ring accumulator bytes."""
    assert len(data)==4075 and data[8]<=1
    out=bytearray(data);idx=struct.unpack_from('<H',data,9)[0];assert idx<100
    pos=43+40*idx
    if not data[8]:
        out[8]=1;struct.pack_into('<Q',out,pos,now);out[pos+8:pos+40]=bytes(32);struct.pack_into('<Q',out,4043,now)
        return bytes(out)
    timestamp=amount(data,pos);previous=amount(data,4043)or timestamp
    struct.pack_into('<Q',out,4043,previous)
    elapsed=max(now-timestamp,0);delta=max(now-previous,0)
    if elapsed==0 or delta==0:return bytes(out)
    cumulatives=[int.from_bytes(data[pos+8:pos+24],'little'),int.from_bytes(data[pos+24:pos+40],'little')]
    increments=[((htfp<<32)//wsol)*delta,((wsol<<32)//htfp)*delta]
    if elapsed>=15:
        idx=(idx+1)%100;struct.pack_into('<H',out,9,idx);pos=43+40*idx;struct.pack_into('<Q',out,pos,now)
    for i in range(2):out[pos+8+16*i:pos+24+16*i]=((cumulatives[i]+increments[i])%(1<<128)).to_bytes(16,'little')
    struct.pack_into('<Q',out,4043,now)
    return bytes(out)

def changed(record,data=None,lamports=None):
    assert record is not None
    out=dict(record)
    if data is not None:out['data_hex']=data.hex()
    if lamports is not None:assert 0<=lamports<=U64;out['lamports']=str(lamports)
    return out

def same_accounts(row,replacements):
    """Compare every tracked role, including aliased fee-payer roles, with no unlisted money flow."""
    before,after=row['before'],row['after'];assert set(before)==set(after)
    assert int(row['fee_lamports'])==5000*len(row['signatures'])
    for role,old in before.items():
        new=after[role]
        if role=='instructions_sysvar':
            if old is None:assert new is None
            else:assert new is not None and {k:v for k,v in old.items()if k!='data_hex'}=={k:v for k,v in new.items()if k!='data_hex'}
            continue
        if role in replacements:want=replacements[role]
        elif old is not None and old['address']==row['payer']:want=changed(old,lamports=int(old['lamports'])-int(row['fee_lamports']))
        else:want=old
        if role.startswith('temp_')and want is None and new is not None:
            assert new['owner']==SYSTEM and not new['executable'] and new['data_hex']=='' and int(new['lamports'])==0
        else:assert new==want,(row['name'],role,'UNEXPECTED_ACCOUNT_DELTA')

def check_rollback(row):
    assert row['status']=='FAILURE'
    same_accounts(row,{})

def check_recover(row,delta):
    assert row['status']=='SUCCESS' and row['phase']=='VERIFIED_LOCAL'
    before,after=row['before'],row['after'];b={k:raw(v)for k,v in before.items()if v is not None}
    h=[i for i in row['instructions']if bytes.fromhex(i['data_hex']).startswith(b'HTFP\x01\x01')];assert len(h)==1
    sources=h[0]['accounts'][6:];source_addresses=[m['pubkey']for m in sources];assert len(set(source_addresses))==len(source_addresses)
    native_mint_pos,native_mint_size=extension(b['mint'],1);assert native_mint_size==108
    expected=amount(b['mint'],native_mint_pos+64)+token(b['custody'])[1]
    replacements={}
    for address in source_addresses:
        roles=[r for r,v in before.items()if v and v['address']==address];assert len(roles)==1
        role=roles[0];pos,size=extension(b[role],2);assert size==8
        expected+=amount(b[role],pos);replacements[role]=changed(before[role],data=replace_u64(b[role],pos,0))
    assert expected==delta and delta>0
    replacements['mint']=changed(before['mint'],data=replace_u64(b['mint'],native_mint_pos+64,0))
    pos,size=extension(b['custody'],2);assert size==8
    c=replace_u64(b['custody'],64,token(b['custody'])[0]+delta);c=replace_u64(c,pos,0)
    replacements['custody']=changed(before['custody'],data=c)
    replacements['inventory']=changed(before['inventory'],data=replace_u64(b['inventory'],12,amount(b['inventory'],12)+delta))
    same_accounts(row,replacements)
    assert token(raw(after['custody']))[0]-amount(raw(after['inventory']),12)==token(b['custody'])[0]-amount(b['inventory'],12)

def check_batch(row,quantities,seq,storage_payers):
    """One/two genuine Process calls with final fence, exact integer native fees and settlement."""
    assert row['status']=='SUCCESS' and row['phase']=='VERIFIED_LOCAL' and row['signature_verification']is True
    assert len(quantities)==len(storage_payers)and 1<=len(quantities)<=2
    before,after=row['before'],row['after'];b={k:raw(v)for k,v in before.items()if v is not None}
    pool=b['pool'];htfp,withheld=token(b['vault_htfp']);wsol=token(b['vault_wsol'])[0]
    obs=b['observation'];epoch=amount(b['clock'],16);now=struct.unpack_from('<q',b['clock'],32)[0]
    assert epoch==row['actual_clock']['epoch'] and now==row['actual_clock']['unix_timestamp'] and now>=1794801600
    credit=volume(b['volume'])['credit'];last=volume(b['volume'])['last'];total={k:0 for k in ('burn','gross','tax','net','creator','protocol','fund','output')}
    processed=[i for i in row['instructions']if bytes.fromhex(i['data_hex']).startswith(b'HTFP\x01\x03')]
    assert len(processed)==len(quantities)
    rent_rate,rent_threshold,rent_burn=struct.unpack('<QdB',b['rent']);assert (rent_rate,rent_threshold,rent_burn)==(5080,1.0,50)
    rent=1488440;assert int((165+128)*rent_rate*rent_threshold)==rent
    replacements={};prefunds=[]
    for i,(q,payer,ins)in enumerate(zip(quantities,storage_payers,processed)):
        assert amount(bytes.fromhex(ins['data_hex']),6)==q and ins['accounts'][9]['pubkey']==payer
        x=effective(pool,htfp,1);y=effective(pool,wsol,0);out=quote(q,x,y,epoch)
        assert out['gross']<=x//1000
        time=max(now,last);available=min(CAPACITY,credit+(time-last)*REFILL);assert 3*out['gross']<=available
        credit=available-3*out['gross'];last=time
        obs=observation(obs,now,y,x)
        for offset,value in ((349,out['protocol']),(365,out['fund']),(405,out['creator'])):pool=replace_u64(pool,offset,amount(pool,offset)+value)
        pool=replace_u64(pool,381,epoch);htfp+=out['net'];withheld+=out['tax'];wsol-=out['output']
        for key,value in out.items():total[key]+=value
        role='temp_'+str(seq+i);assert before.get(role)is None or before[role]['owner']==SYSTEM
        prior=before[role];prefund=0 if prior is None else int(prior['lamports']);deposit=max(rent-prefund,0)
        if prior is not None:assert not prior['executable']and prior['data_hex']==''
        replacements[role]=prior;prefunds.append({'sequence':seq+i,'prefund':prefund,'rent':rent,'deposit':deposit,'storage_payer':payer})
    v=volume(b['volume']);assert v['sequence']==seq and v['active']==0 and v['nonce']==0
    want_v=bytearray(b['volume']);struct.pack_into('<QqQ',want_v,43,credit,last,seq+len(quantities));want_v[67:80]=bytes(13)
    replacements['volume']=changed(before['volume'],data=bytes(want_v))
    replacements['mint']=changed(before['mint'],data=replace_u64(b['mint'],36,amount(b['mint'],36)-total['burn']))
    replacements['inventory']=changed(before['inventory'],data=replace_u64(b['inventory'],12,amount(b['inventory'],12)-sum(quantities)))
    replacements['custody']=changed(before['custody'],data=replace_u64(b['custody'],64,token(b['custody'])[0]-sum(quantities)))
    pos,size=extension(b['vault_htfp'],2);assert size==8
    h=replace_u64(replace_u64(b['vault_htfp'],64,htfp),pos,withheld)
    replacements['vault_htfp']=changed(before['vault_htfp'],data=h)
    replacements['vault_wsol']=changed(before['vault_wsol'],data=replace_u64(b['vault_wsol'],64,wsol),lamports=int(before['vault_wsol']['lamports'])-total['output'])
    replacements['pool']=changed(before['pool'],data=pool)
    replacements['observation']=changed(before['observation'],data=obs)
    replacements['reserve']=changed(before['reserve'],lamports=int(before['reserve']['lamports'])+total['output'])
    same_accounts(row,replacements)
    assert token(raw(after['custody']))[0]-amount(raw(after['inventory']),12)==token(b['custody'])[0]-amount(b['inventory'],12)==920
    return {**total,'prefunds':prefunds,'credit':credit,'sequence':seq+len(quantities)}
