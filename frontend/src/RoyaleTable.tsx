import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import './royale-table.css';

type Seat = {id:string; name:string; card_count:number; position?:number|null; provisional?:boolean};
type TableState = {players:Seat[]; current_player_id:string|null; current_rank:string|null; pile_size:number; turn_seconds_left:number; paused:boolean; last_play?:{player_id:string; card_count:number; claimed_rank:string}|null};
const layouts = [[], [[50,90]], [[50,90],[50,10]], [[50,90],[16,21],[84,21]], [[50,90],[13,50],[50,10],[87,50]], [[50,90],[14,68],[23,17],[77,17],[86,68]], [[50,90],[13,66],[21,20],[50,9],[79,20],[87,66]]];
const suits = ['\u2660','\u2665','\u2663','\u2666'];
const ordinal = (n:number) => `${n}${n===1?'st':n===2?'nd':n===3?'rd':'th'}`;
export default function RoyaleTable({game,playerId,motion}: {game:TableState;playerId:string;motion:boolean}) {
  const self = game.players.find(p=>p.id===playerId);
  const order = self ? [...game.players.slice(game.players.indexOf(self)), ...game.players.slice(0,game.players.indexOf(self))] : game.players;
  const locations = layouts[order.length] || layouts[6];
  const last = game.last_play;
  const previous = useRef(game.pile_size);
  const [arrival,setArrival] = useState({count:0, first:0, tick:0});
  useEffect(()=>{
    const before=previous.current;
    previous.current=game.pile_size;
    if(game.pile_size<=before || !motion) {setArrival(a=>a.count?{...a,count:0}:a);return;}
    setArrival(a=>({count:Math.min(game.pile_size-before,6),first:Math.min(before,14),tick:a.tick+1}));
  },[game.pile_size,motion]);
  const seat = locations[order.findIndex(p=>p.id===last?.player_id)] || [50,50];
  const cards = Math.min(game.pile_size, 14);
  return <section className={'rt-stage'+(motion?' rt-motion':'')} aria-label="Bluff Royale table">
    <div className="rt-felt" />
    <div className="rt-claim"><small>{game.current_rank?'ROUND CLAIM':'NEW ROUND'}</small><strong>{game.current_rank || 'Choose a rank'}</strong></div>
    <div className="rt-pot" aria-hidden="true">{Array.from({length:cards},(_,i)=>{
      const x=(i*37%85)-42, y=(i*29%49)-24;
      const animate=motion && arrival.count>0 && i>=Math.min(arrival.first,Math.max(0,cards-arrival.count));
      return <div key={animate?`${i}-${arrival.tick}`:i} className={'rt-back'+(animate?' rt-deal':'')} style={{'--x':`${x}px`,'--y':`${y}px`,'--r':`${i*59%113-56}deg`,'--sx':`${(seat[0]-50)*2.1}px`,'--sy':`${(seat[1]-50)*2.2}px`,animationDelay:`${i%6*28}ms`} as CSSProperties}>{suits[0]}</div>;
    })}</div>
    <div className="rt-count"><b>{game.pile_size}</b> {game.pile_size===1?'card':'cards'} in the pot</div>
    {last && <p className="rt-last">{order.find(p=>p.id===last.player_id)?.name} claimed <b>{last.card_count} &times; {last.claimed_rank}</b></p>}
    {order.map((p,i)=>{const [x,y]=locations[i];const active=p.id===game.current_player_id;
      return <div key={p.id} className={'rt-seat'+(active?' rt-active':'')+(p.position?' rt-finished':'')} style={{left:`${x}%`,top:`${y}%`}}>
        <div className="rt-avatar" aria-hidden="true">{suits[i%4]}</div>
        <b title={p.name}>{p.id===playerId?'You':p.name}</b>
        <small>{p.position?`${ordinal(p.position)} place`:p.provisional?'Finish pending':`${p.card_count} cards`}</small>
        {active&&<span className={'rt-clock'+(game.turn_seconds_left<=10?' rt-urgent':'')} aria-label={game.paused?'Paused turn':`Turn: ${game.turn_seconds_left} seconds left`}>{game.paused?'II':game.turn_seconds_left}</span>}
      </div>;
    })}
  </section>;
}
