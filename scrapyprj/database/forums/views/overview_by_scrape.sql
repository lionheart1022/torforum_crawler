create view `overview_by_scrape` as
select 
    ifnull(`ScrapeId`,0) as 'ScrapeId', 
    ifnull(`ScrapeStart`, 0) as 'ScrapeStart', 
    `ScrapeDuration` as 'ScrapeDuration',
    `ExitReason` as 'ExitReason',
    ifnull(`Thread`, 0) as 'Thread', 
    ifnull(`Message`, 0)  as 'Message', 
    ifnull(`MessagePropVal`, 0) as 'MessagePropVal', 
    ifnull(`User`, 0) as 'User', 
    ifnull(`UserPropVal`, 0) as 'UserPropVal'

from (
    (select `id` as 'ScrapeID', `start` as 'ScrapeStart', timediff(`end`,`start`) as 'ScrapeDuration', `reason` as 'ExitReason' from `scrape`) as s
    left join (select `scrape`, count(1) as 'User' from `user` group by `scrape`) as u on u.scrape=s.ScrapeID
    left join (
        select `scrape`, sum(`Message`) as 'Message' from 
        (
            (select `scrape`, ifnull(count(1),0) as 'Message' from `message` group by `scrape`)
            union all
            (select `scrape`, ifnull(count(1),0) as 'Message' from `message_audit` group by `scrape`)
        ) as sumed_msg 
        group by `scrape`

        ) as m on m.scrape=s.ScrapeID
    left join 
    (
        select `scrape`, sum(`MessagePropVal`) as 'MessagePropVal' from 
        (
            (select `scrape`, ifnull(count(1),0) as 'MessagePropVal' from `message_propval` group by `scrape`)
            union all
            (select `scrape`, ifnull(count(1),0) as 'MessagePropVal' from `message_propvalaudit` group by `scrape`)
        ) as sumedmv 
        group by `scrape`
    ) as mv on mv.scrape=s.ScrapeID
    left join (select `scrape`, count(1) as 'Thread' from `thread` group by `scrape`) as t on t.`scrape`=s.`ScrapeID`
    left join 
    (
        select `scrape`, sum(`UserPropVal`) as 'UserPropVal' from 
        (
            (select `scrape`, ifnull(count(1),0) as 'UserPropVal' from `user_propval` group by `scrape`)
            union all
            (select `scrape`, ifnull(count(1),0) as 'UserPropVal' from `user_propvalaudit` group by `scrape`)
        ) as sumeduv 
        group by sumeduv.`scrape`
    )as uv on uv.`scrape`=s.`ScrapeID`
)
order by `ScrapeStart` desc 
