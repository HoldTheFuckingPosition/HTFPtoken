"""Independent integer quote from retained official curve/fee source; no runtime."""
D=1000000
def ceil_ratio(n,d):return (n+d-1)//d
def token_tax(n,active=True):return ceil_ratio(n*800,10000) if active else 0
def quote(gross,x,y,htfp_in,enabled,side,active=True):
 native_in_tax=token_tax(gross,active) if htfp_in else 0;amount=gross-native_in_tax
 creator_rate=2500 if enabled else 0;on_input=side==0 or (side==1 and not htfp_in) or (side==2 and htfp_in)
 if on_input:
  total=ceil_ratio(amount*(2500+creator_rate),D);creator=total*creator_rate//(2500+creator_rate);trade=total-creator;curve_in=amount-total
 else:trade=ceil_ratio(amount*2500,D);creator=0;curve_in=amount-trade
 curve_out=curve_in*y//(x+curve_in)
 if on_input:out=curve_out
 else:creator=ceil_ratio(curve_out*creator_rate,D);out=curve_out-creator
 native_out_tax=token_tax(out,active) if not htfp_in else 0
 return dict(gross_in=gross,native_in_tax=native_in_tax,actual_input=amount,trade_fee=trade,protocol_fee=trade*120000//D,fund_fee=trade*40000//D,creator_fee=creator,creator_fee_on_input=on_input,gross_out=out,native_out_tax=native_out_tax,recipient_out=out-native_out_tax,curve_in=curve_in,curve_out=curve_out)
