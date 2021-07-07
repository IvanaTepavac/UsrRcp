import clearbit

clearbit.key = 'sk_832247e2aaf7526907221858efb3e4f5'


def get_user_and_company_data(email):
    response = clearbit.Enrichment.find(email={email}, stream=True)

    if not response:
        return

    if response['person'] is not None:
        print(response['person']['name']['fullName'])

    if response['company'] is not None:
        print(response['company']['name'])
