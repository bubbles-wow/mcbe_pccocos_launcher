from dataclasses import dataclass, asdict, field

@dataclass
class BaseEntity:
    def update(self, data: dict):
        if not data:
            return
        for key, value in data.items():
            if hasattr(self, key):
                attr = getattr(self, key)
                if isinstance(value, dict) and hasattr(attr, 'update'):
                    attr.update(value)
                else:
                    setattr(self, key, value)
                
    def to_dict(self):
        return asdict(self)
    
    def to_save_dict(self):
        return self.to_dict()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BaseEntity':
        if not data:
            return cls()
        
        init_kwargs = {}
        # 获取 dataclass 的所有字段定义
        fields = cls.__dataclass_fields__
        
        for field_name, field_def in fields.items():
            if field_name not in data:
                continue
                
            value = data[field_name]
            field_type = field_def.type
            
            if isinstance(value, dict):
                if hasattr(field_type, 'from_dict') and callable(field_type.from_dict):
                    init_kwargs[field_name] = field_type.from_dict(value)
                else:
                    init_kwargs[field_name] = value
            else:
                init_kwargs[field_name] = value
                
        return cls(**init_kwargs)
    