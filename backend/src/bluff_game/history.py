import json
from datetime import datetime,timezone
from sqlalchemy import create_engine,String,DateTime,Text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,sessionmaker
class Base(DeclarativeBase):pass
class Match(Base):
 __tablename__='matches';id:Mapped[int]=mapped_column(primary_key=True);room_code:Mapped[str]=mapped_column(String(12),index=True);started_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));finished_at:Mapped[datetime]=mapped_column(DateTime(timezone=True));players_json:Mapped[str]=mapped_column(Text);standings_json:Mapped[str]=mapped_column(Text)
class History:
 def __init__(self,url):
  args={'check_same_thread':False}if url.startswith('sqlite')else{};self.engine=create_engine(url,connect_args=args);Base.metadata.create_all(self.engine);self.Session=sessionmaker(self.engine)
 def save(self,room):
  if room.history_saved:return
  with self.Session()as s:s.add(Match(room_code=room.id,started_at=datetime.fromtimestamp(room.started_at,tz=timezone.utc),finished_at=datetime.now(timezone.utc),players_json=json.dumps([{'id':p.id,'name':p.name}for p in room.game.players]),standings_json=json.dumps(room.game.finishing_order)));s.commit();room.history_saved=True
 def by_player(self,name,limit=20):
  with self.Session()as s:
   rows=s.query(Match).order_by(Match.id.desc()).limit(200).all();out=[]
   for r in rows:
    players=json.loads(r.players_json)
    if any(p['name'].casefold()==name.casefold()for p in players):out.append({'room_code':r.room_code,'started_at':r.started_at,'finished_at':r.finished_at,'players':players,'standings':json.loads(r.standings_json)})
    if len(out)>=limit:break
   return out
