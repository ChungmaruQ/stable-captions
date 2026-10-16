"""Request options for the deployed caption models; active deployment stays explicit."""
def generation_options(deployment,reasoning_tokens=1600,legacy_tokens=400):
    name=deployment.lower()
    if name == 'gpt-6-luna' or name.startswith('gpt-6-luna-'):
        return {'max_completion_tokens':reasoning_tokens,'reasoning_effort':'none'}
    if name.startswith('gpt-5'):
        return {'max_completion_tokens':reasoning_tokens,'reasoning_effort':'minimal'}
    return {'max_tokens':legacy_tokens,'temperature':0}
