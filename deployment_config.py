"""Validate deploy paths without reading or displaying credentials."""
from pathlib import Path

def validate_deployment(env,source):
    source=Path(source).resolve()
    if env.get('THANA_ENV')!='production':raise ValueError('Deployment launcher requires THANA_ENV=production')
    if not env.get('THANA_DATA_DIR') or not env.get('THANA_PLATFORM_DB'):raise ValueError('Set both persistent data paths')
    data=Path(env['THANA_DATA_DIR']);database=Path(env['THANA_PLATFORM_DB'])
    if not data.is_absolute() or not database.is_absolute():raise ValueError('Storage paths must be absolute')
    data=data.resolve();database=database.resolve()
    if data==source or source in data.parents:raise ValueError('Persistent storage must be outside the source checkout')
    if data!=database.parent:raise ValueError('Platform database must be directly inside the persistent data directory')
    if env.get('THANA_STAGING_ENABLED')=='1':
        username=env.get('THANA_STAGING_USER','reviewer')
        if not username or ':' in username or len(env.get('THANA_STAGING_PASSWORD',''))<16:raise ValueError('Configure private staging review access')
    try:port=int(env.get('PORT','8035'))
    except ValueError:raise ValueError('PORT must be numeric')
    if not 1<=port<=65535:raise ValueError('PORT is out of range')
    return {'data':str(data),'database':str(database),'port':port,'staging':env.get('THANA_STAGING_ENABLED')=='1'}
