TABS = {'intake':'原件采信','registry':'槽位版本','custody':'查验占位','exposure':'门区暴露','capacity':'余量对账',
        'history':'批次留档','certificate':'冷库证据'}
KINDS = {'closed':'闭门','warm':'温超限','cooled':'温合格','missing_temp':'温度缺证','missing_slot':'槽位缺证','missing_door':'门态缺证'}
CODES = {'WIDTH':'列数不符','MISSING':'必填字段缺失','MOVE_FIELDS':'动作字段不符','TIME':'时间无效',
         'SIGNAL':'门信号无效','EVENT_CONFLICT':'同号日志矛盾','DUP_PACKET':'重复收件','SLOT_AMBIGUOUS':'槽位版本冲突',
         'SLOT_UNKNOWN':'缺少槽位证据','CAPACITY_EXCEEDED':'调入超出槽位容量','INVALID_LIFECYCLE':'无效入出库动作',
         'SIMULTANEOUS':'同刻动作冲突','LOT_UNKNOWN':'未知货批','TICKET_MISMATCH':'查验单不匹配','ALREADY_FROZEN':'货批已冻结',
         'FROZEN_OUT':'冻结件不得出库','DOOR_BOUNCE':'门信号抖动','DOOR_CONFLICT':'同刻门态矛盾',
         'TEMP_INVALID':'温度读数无效','TEMP_CONFLICT':'同刻温度矛盾'}
